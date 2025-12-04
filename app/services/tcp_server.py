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
    sock.sendall(message.encode("utf-8"))

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
        game_id = None
        try:
            for line in recv_lines(conn):
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    send_json(conn, {"type": "error", "message": "invalid json"})
                    continue

                msg_type = payload.get("type")
                if msg_type == "join":
                    player_name = payload.get("player")
                    game_id = payload.get("game_id")
                    if not player_name or not game_id:
                        send_json(conn, {"type": "error", "message": "player and game_id required"})
                        continue
                    try:
                        session = self.manager.socket_join(
                            game_id, player_name, ClientConn(player_name, conn, addr)
                        )
                        send_json(conn, {"type": "joined", "state": session.snapshot()})
                    except Exception as exc:
                        send_json(conn, {"type": "error", "message": str(exc)})
                elif msg_type in ("roll", "move", "sync_time"):
                    if not game_id or not player_name:
                        send_json(conn, {"type": "error", "message": "join first"})
                        continue
                    payload["player"] = player_name
                    try:
                        self.manager.enqueue_action(game_id, payload)
                    except Exception as exc:
                        send_json(conn, {"type": "error", "message": str(exc)})
                else:
                    send_json(conn, {"type": "error", "message": "unknown message type"})
        except Exception as exc:
            logger.exception("Client handler error: %s", exc)
        finally:
            logger.info("Client disconnected %s", addr)
            conn.close()


_tcp_server: TCPServer | None = None


def start_tcp_server() -> None:
    settings = get_settings()
    manager = get_game_manager()
    global _tcp_server
    if _tcp_server is None:
        _tcp_server = TCPServer(manager, settings.tcp_host, settings.tcp_port)
    _tcp_server.start()
