import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from uvicorn.protocols.utils import ClientDisconnected

from app.core.settings import get_settings

logger = logging.getLogger(__name__)

router = APIRouter()


async def tcp_proxy(ws: WebSocket, player: str, color: str | None) -> None:
    settings = get_settings()
    tcp_host = "127.0.0.1" if settings.tcp_host in ("0.0.0.0", "::") else settings.tcp_host
    logger.info("WS bridge opening TCP to %s:%s for player %s color %s", tcp_host, settings.tcp_port, player, color)
    reader, writer = await asyncio.open_connection(tcp_host, settings.tcp_port)

    async def send_tcp(payload: dict) -> None:
        message = json.dumps(payload, ensure_ascii=True) + "\n"
        writer.write(message.encode("utf-8"))
        try:
            await writer.drain()
        except Exception:
            pass

    await send_tcp({"type": "join", "player": player, "color": color})
    logger.info("WS->TCP sent join for %s %s", player, color)

    async def ws_to_tcp():
        async for msg in ws.iter_text():
            try:
                data = json.loads(msg)
                if isinstance(data, dict):
                    await send_tcp(data)
                    logger.debug("WS->TCP payload %s", data)
                else:
                    await ws.send_text(json.dumps({"type": "error", "message": "invalid message"}))
            except json.JSONDecodeError:
                await ws.send_text(json.dumps({"type": "error", "message": "invalid json"}))
            except (WebSocketDisconnect, ClientDisconnected):
                logger.info("WS->TCP websocket disconnect for %s", player)
                break
            except Exception:
                logger.exception("WS->TCP loop error")
                break
        logger.info("WS->TCP loop completed for %s", player)

    async def tcp_to_ws():
        while not reader.at_eof():
            line = await reader.readline()
            if not line:
                break
            try:
                payload = line.decode("utf-8").strip()
                logger.debug("TCP->WS payload %s", payload)
                await ws.send_text(payload)
            except (WebSocketDisconnect, ClientDisconnected):
                logger.info("TCP->WS websocket disconnected for %s", player)
                break
            except Exception:
                logger.exception("TCP->WS loop error")
                break
        logger.info("TCP->WS loop completed for %s", player)

    ws_task = asyncio.create_task(ws_to_tcp())
    tcp_task = asyncio.create_task(tcp_to_ws())
    done, pending = await asyncio.wait({ws_task, tcp_task}, return_when=asyncio.FIRST_COMPLETED)
    logger.info("WS bridge tasks done=%s pending=%s for %s", {d._coro.__name__: d.done() for d in done}, len(pending), player)
    for task in pending:
        task.cancel()
    try:
        writer.close()
        await writer.wait_closed()
    except Exception:
        pass
    logger.info("WS bridge closed for %s", player)


@router.websocket("/ws/tcp")
async def websocket_tcp_bridge(ws: WebSocket):
    await ws.accept()
    player = ws.query_params.get("player")
    color = ws.query_params.get("color")
    logger.info("WS connected: player=%s color=%s", player, color)
    if not player:
        await ws.send_text(json.dumps({"type": "error", "message": "player is required"}))
        await ws.close()
        return
    try:
        await tcp_proxy(ws, player, color)
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected: %s", player)
    except Exception as exc:
        logger.exception("WS TCP bridge error: %s", exc)
        try:
            await ws.send_text(json.dumps({"type": "error", "message": str(exc)}))
        except Exception:
            pass
        try:
            await ws.close()
        except Exception:
            pass
