from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import dataclass, field
from queue import Queue, Empty
from typing import Dict, List, Optional
from uuid import uuid4

from app.core.settings import get_settings
from app.services.berkeley import BerkeleyClock
from app.services.parques_engine import ParquesEngine

logger = logging.getLogger(__name__)


def _safe_send(sock, payload: dict, lock: threading.Lock) -> None:
    """Send JSON payload with newline delimiter."""
    message = json.dumps(payload, ensure_ascii=True) + "\n"
    data = message.encode("utf-8")
    with lock:
        try:
            sock.sendall(data)
        except OSError:
            logger.warning("Failed to send message to client")


@dataclass
class ClientConn:
    player_name: str
    socket: any
    address: tuple
    send_lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def send(self, payload: dict) -> None:
        _safe_send(self.socket, payload, self.send_lock)


@dataclass
class GameSession:
    game_id: str
    status: str = "waiting"  # waiting | running | finished
    engine: ParquesEngine = field(default_factory=ParquesEngine)
    berkeley: BerkeleyClock = field(default_factory=BerkeleyClock)
    last_state: dict = field(default_factory=dict)
    thread: Optional[threading.Thread] = None
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
                "state": state,
            }

    def broadcast(self, payload: dict) -> None:
        for conn in list(self.clients.values()):
            conn.send(payload)


class GameManager:
    """Coordinates game sessions, actions and broadcasts."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.sessions: Dict[str, GameSession] = {}
        self.sessions_lock = threading.Lock()

    def create_game(self) -> GameSession:
        game_id = uuid4().hex[:8]
        session = GameSession(game_id=game_id)
        with self.sessions_lock:
            self.sessions[game_id] = session
        logger.info("Created game %s", game_id)
        return session

    def get_session(self, game_id: str) -> GameSession:
        session = self.sessions.get(game_id)
        if session is None:
            raise KeyError("Game not found")
        return session

    def join_game(self, game_id: str, player_name: str, color_index: Optional[int] = None) -> GameSession:
        session = self.get_session(game_id)
        session.add_player(player_name, color_index, self.settings.game_max_players)
        logger.info("Player %s joined %s", player_name, game_id)
        # Auto-start when at least 2 players
        if session.status == "waiting" and len(session.engine.players) >= 2:
            self.start_game(game_id)
        return session

    def socket_join(self, game_id: str, player_name: str, conn: ClientConn) -> GameSession:
        session = self.join_game(game_id, player_name)
        session.attach_connection(player_name, conn)
        return session

    def start_game(self, game_id: str) -> GameSession:
        session = self.get_session(game_id)
        with session.lock:
            if session.status == "running":
                return session
            if len(session.engine.players) < 2:
                raise ValueError("Need at least 2 players to start")
            session.engine.start()
            session.status = "running"
        thread = threading.Thread(target=self._run_game_loop, args=(session,), daemon=True)
        session.thread = thread
        thread.start()
        logger.info("Game %s started", game_id)
        return session

    def enqueue_action(self, game_id: str, action: dict) -> None:
        session = self.get_session(game_id)
        session.action_queue.put(action)

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

    def stop_game(self, game_id: str) -> None:
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
