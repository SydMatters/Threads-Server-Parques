from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.settings import get_settings
from app.db.session import init_db

from app.api.routes.health import router as health_router
from app.api.routes.games import router as games_router
from app.api.routes.players import router as players_router
from app.services.tcp_server import start_tcp_server

settings = get_settings()

app = FastAPI(title=settings.app_name, debug=settings.debug)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    start_tcp_server()


app.include_router(health_router, prefix="/health")
app.include_router(games_router, prefix="/games")
app.include_router(players_router, prefix="/players")
