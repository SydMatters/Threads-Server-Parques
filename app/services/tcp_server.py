import json
import logging
import socket
import threading
from typing import Tuple

from app.core.settings import get_settings
from app.services.game_manager import ClientConn, GameManager, get_game_manager


def recv_lines(sock: socket.socket):
    """Yield lines delimited by newline from a socket."""
    buffer = b""
    while True:
        data = sock.recv(4096)
        if not data:
            break
        buffer += data
        while b"\n" in buffer:
            line, buffer = buffer.split(b"\n", 1)
            yield line.decode("utf-8").strip()


def send_json(sock: socket.socket, payload: dict) -> None:
    message = json.dumps(payload, ensure_ascii=True) + "\n"
    try:
        peer = sock.getpeername()
    except OSError:
        peer = "disconnected"
    logger.debug("TCP -> %s: %s", peer, payload)
    try:
        sock.sendall(message.encode("utf-8"))
    except OSError:
        logger.info("TCP send failed to %s", peer)

logger = logging.getLogger(__name__)


class TCPServer:
    """Simple TCP server handling JSON messages line-delimited."""

    def __init__(self, manager: GameManager, host: str, port: int) -> None:
        self.manager = manager
        self.host = host
        self.port = port
        self.sock: socket.socket | None = None
        self.accept_thread: threading.Thread | None = None
        self.running = False

    def start(self) -> None:
        if self.running:
            return
        self.running = True
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.host, self.port))
        self.sock.listen()
        self.accept_thread = threading.Thread(target=self._accept_loop, daemon=True)
        self.accept_thread.start()
        logger.info("TCP server listening on %s:%s", self.host, self.port)

    def _accept_loop(self) -> None:
        assert self.sock
        while self.running:
          try:
            conn, addr = self.sock.accept()
            threading.Thread(target=self._handle_client, args=(conn, addr), daemon=True).start()
          except OSError:
              break

    def _handle_client(self, conn: socket.socket, addr: Tuple[str, int]) -> None:
        logger.info("Client connected %s", addr)
        player_name = None
        try:
            for line in recv_lines(conn):
                if not line:
                    continue
                logger.debug("TCP <- %s: %s", addr, line)
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    logger.info("Invalid JSON from %s: %s", addr, line)
                    break

                msg_type = payload.get("type")
                if msg_type == "join":
                    player_name = payload.get("player")
                    color_name = payload.get("color")
                    if not player_name:
                        send_json(conn, {"type": "error", "message": "player required"})
                        continue
                    try:
                        session = self.manager.socket_join(
                            player_name, ClientConn(player_name, conn, addr), color_name=color_name
                        )
                        state = session.snapshot()
                        send_json(conn, {"type": "joined", "state": state})
                        session.broadcast({"type": "state", "state": state})
                        logger.info("Join processed for %s, color %s", player_name, color_name)
                    except Exception as exc:
                        send_json(conn, {"type": "error", "message": str(exc)})
                elif msg_type in ("roll", "move", "sync_time"):
                    if not player_name:
                        send_json(conn, {"type": "error", "message": "join first"})
                        continue
                    payload["player"] = player_name
                    try:
                        self.manager.enqueue_action(payload)
                    except Exception as exc:
                        send_json(conn, {"type": "error", "message": str(exc)})
                elif msg_type == "start":
                    try:
                        logger.info("TCP start request from %s", player_name)
                        session = self.manager.start_game(started_by=player_name)
                        state = session.snapshot()
                        session.broadcast({"type": "state", "state": state})
                        logger.info("TCP broadcast state after start: %s", state)
                    except Exception as exc:
                        send_json(conn, {"type": "error", "message": str(exc)})
                else:
                    send_json(conn, {"type": "error", "message": "unknown message type"})
        except ConnectionResetError:
            logger.info("Client reset connection %s", addr)
        except Exception as exc:
            logger.exception("Client handler error: %s", exc)
        finally:
            if player_name:
                try:
                    session = self.manager.get_session()
                    with session.lock:
                        removed = session.clients.pop(player_name, None)
                        if removed:
                            logger.info("Detached client %s from session", player_name)
                except Exception:
                    logger.exception("Failed to detach client %s", player_name)
            logger.info("Client disconnected %s", addr)
            try:
                conn.close()
            except Exception:
                pass


_tcp_server: TCPServer | None = None


def start_tcp_server() -> None:
    settings = get_settings()
    manager = get_game_manager()
    global _tcp_server
    if _tcp_server is None:
        _tcp_server = TCPServer(manager, settings.tcp_host, settings.tcp_port)
    _tcp_server.start()
