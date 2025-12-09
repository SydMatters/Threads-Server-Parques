from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import dataclass, field
from queue import Queue, Empty
from typing import Dict, List, Optional

from app.core.settings import get_settings
from app.services.berkeley import BerkeleyClock
from app.services.parques_engine import ParquesEngine
from app.services.parques_engine import color_index_from_name

logger = logging.getLogger(__name__)

DEFAULT_GAME_ID = "default"


def _safe_send(sock, payload: dict, lock: threading.Lock) -> bool:
    """Send JSON payload with newline delimiter. Returns True on success."""
    message = json.dumps(payload, ensure_ascii=True) + "\n"
    data = message.encode("utf-8")
    with lock:
        try:
            sock.sendall(data)
            return True
        except OSError:
            logger.warning("Failed to send message to client")
            return False


@dataclass
class ClientConn:
    player_name: str
    socket: any
    address: tuple
    send_lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def send(self, payload: dict) -> bool:
        return _safe_send(self.socket, payload, self.send_lock)


@dataclass
class GameSession:
    game_id: str
    status: str = "waiting"  # waiting | running | finished
    engine: ParquesEngine = field(default_factory=ParquesEngine)
    berkeley: BerkeleyClock = field(default_factory=BerkeleyClock)
    last_state: dict = field(default_factory=dict)
    thread: Optional[threading.Thread] = None
    host: Optional[str] = None
    lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    action_queue: Queue = field(default_factory=Queue, repr=False)
    clients: Dict[str, ClientConn] = field(default_factory=dict)  # player_name -> conn

    def add_player(self, player_name: str, color_index: Optional[int], max_players: int) -> None:
        with self.lock:
            if self.status not in ("waiting", "running"):
                raise ValueError("Game already finished")
            if any(p.name == player_name for p in self.engine.players):
                # Already joined; allow re-attachment
                return
            if len(self.engine.players) >= max_players:
                raise ValueError("Game is full")
            self.engine.add_player(player_name, color_index)
            if self.host is None:
                self.host = player_name

    def attach_connection(self, player_name: str, conn: ClientConn) -> None:
        with self.lock:
            self.clients[player_name] = conn

    def snapshot(self) -> dict:
        with self.lock:
            state = self.engine.state()
            state["clock_ms"] = self.berkeley.now_ms()
            return {
                "game_id": self.game_id,
                "status": self.status,
                "host": self.host,
                "state": state,
            }

    def broadcast(self, payload: dict) -> None:
        """Broadcast to all attached clients, pruning dead sockets."""
        dead = []
        for name, conn in list(self.clients.items()):
            ok = conn.send(payload)
            if not ok:
                dead.append(name)
        for name in dead:
            self.clients.pop(name, None)
            logger.info("Removed dead client connection for %s", name)


class GameManager:
    """Coordinates game sessions, actions and broadcasts."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.sessions: Dict[str, GameSession] = {DEFAULT_GAME_ID: GameSession(game_id=DEFAULT_GAME_ID)}
        self.sessions_lock = threading.Lock()

    def create_game(self) -> GameSession:
        """Always return the single game session."""
        return self.get_session()

    def get_session(self, game_id: str | None = None) -> GameSession:
      try:  
        if game_id and game_id != DEFAULT_GAME_ID:
            raise ValueError("Only single default game is supported")
        session = self.sessions.get(DEFAULT_GAME_ID)
        if session is None:
            session = GameSession(game_id=DEFAULT_GAME_ID)
            with self.sessions_lock:
                self.sessions[DEFAULT_GAME_ID] = session
        return session
      except Exception as e:
        logger.exception(f"Error {e} in get_session")
        raise e

    def join_game(self, player_name: str, color_name: Optional[str] = None) -> GameSession:
        try:
          
          session = self.get_session()
          color_index = color_index_from_name(color_name) if color_name else None
          session.add_player(player_name, color_index, self.settings.game_max_players)
          logger.info("Player %s joined %s", player_name, session.game_id)
          return session
        except Exception as e:
          logger.exception(f"Error {e} in join_game")
          raise e

    def socket_join(self, player_name: str, conn: ClientConn, color_name: Optional[str] = None) -> GameSession:
        try:
          session = self.join_game(player_name, color_name=color_name)
          session.attach_connection(player_name, conn)
          return session
        except Exception as e:
          logger.exception(f"Error {e} in socket_join")
          raise e

    def start_game(self, started_by: Optional[str] = None) -> GameSession:
      try:
        session = self.get_session()
        with session.lock:
            if session.status == "running":
                return session
            if len(session.engine.players) < 2:
                raise ValueError("Need at least 2 players to start")
            if session.host and started_by and session.host != started_by:
                raise ValueError("Only host can start the game")
            session.engine.start()
            session.status = "running"
        thread = threading.Thread(target=self._run_game_loop, args=(session,), daemon=True)
        session.thread = thread
        thread.start()
        logger.info("Game %s started by %s with players %s", session.game_id, started_by or session.host, [p.name for p in session.engine.players])
        try:
            session.broadcast({"type": "state", "state": session.snapshot()})
        except Exception:
            logger.exception("Failed to broadcast start state")
        return session
      except Exception as e:
        logger.exception(f"Error {e} in start_game")
        raise e

    def enqueue_action(self, action: dict) -> None:
        session = self.get_session()
        logger.info("Queue action: %s", action)
        session.action_queue.put(action)

    def move_token(self, player_name: str, token_id: int, steps: Optional[int] = None) -> dict:
        session = self.get_session()
        with session.lock:
            if session.status != "running":
                raise ValueError("El juego no ha comenzado")
            if session.engine.current_player.name != player_name:
                raise ValueError("No es tu turno")
            session.engine.move_token(player_name, [token_id], steps)
            logger.info("Player %s moved token %s with steps %s", player_name, token_id, steps)
            snapshot = session.snapshot()
            return {"state": snapshot}

    def _run_game_loop(self, session: GameSession) -> None:
        """Consume actions and broadcast state; also sync clock periodically."""
        last_sync = time.time()
        try:
            while session.status == "running":
                try:
                    action = session.action_queue.get(timeout=1.0)
                except Empty:
                    action = None

                if action:
                    self._process_action(session, action)

                if session.engine.winner:
                    session.status = "finished"
                    session.broadcast({"type": "finished", "winner": session.engine.winner})
                    break

                # Periodic clock sync broadcast
                if time.time() - last_sync >= self.settings.berkeley_sync_interval_sec:
                    session.broadcast(
                        {
                            "type": "sync_update",
                            "clock_ms": session.berkeley.now_ms(),
                            "offset_ms": session.berkeley.offset_ms,
                        }
                    )
                    last_sync = time.time()
        except Exception:
            logger.exception("Error in game loop for %s", session.game_id)
            with session.lock:
                session.status = "finished"

    def _process_action(self, session: GameSession, action: dict) -> None:
        """Apply a roll/move/sync action coming from sockets."""
        try:
            action_type = action.get("type")
            player = action.get("player")
            if action_type == "roll":
                dice = session.engine.roll_for_current_player()
                session.broadcast({"type": "rolled", "player": player, "dice": dice, "state": session.snapshot()})
            elif action_type == "move":
                token_id = int(action.get("token_id", 0))
                steps = action.get("steps")
                session.engine.move_token(player, token_id, steps)
                session.broadcast({"type": "state", "state": session.snapshot()})
            elif action_type == "sync_time":
                client_time = action.get("client_time_ms")
                if client_time is not None:
                    offset = session.berkeley.sync([float(client_time)])
                    conn = session.clients.get(player)
                    if conn:
                        conn.send(
                            {"type": "sync_ack", "offset_ms": offset, "server_time_ms": session.berkeley.now_ms()}
                        )
            else:
                conn = session.clients.get(player)
                if conn:
                    conn.send({"type": "error", "message": "Unknown action"})
        except Exception as exc:
            logger.exception("Failed processing action")
            conn = session.clients.get(action.get("player"))
            if conn:
                conn.send({"type": "error", "message": str(exc)})

    def stop_game(self, game_id: str | None = None) -> None:
        session = self.get_session(game_id)
        with session.lock:
            session.status = "finished"
        logger.info("Game %s stopped", game_id)
        session.broadcast({"type": "stopped"})

    def list_games(self) -> List[dict]:
        with self.sessions_lock:
            return [session.snapshot() for session in self.sessions.values()]


_game_manager = GameManager()


def get_game_manager() -> GameManager:
    return _game_manager
