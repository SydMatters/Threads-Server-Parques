from functools import lru_cache

from pydantic import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Parques Backend"
    debug: bool = True
    api_prefix: str = "/api"
    database_url: str = "sqlite:///./test.db"
    allowed_origins: list[str] = ["*"]
    game_max_players: int = 4
    berkeley_sync_interval_sec: int = 30
    tcp_host: str = "0.0.0.0"
    tcp_port: int = 9000

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
