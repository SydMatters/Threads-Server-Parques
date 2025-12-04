from pydantic import BaseModel


class GameState(BaseModel):
    game_id: str
    status: str
    state: dict


class GameCreate(BaseModel):
    name: str | None = None
