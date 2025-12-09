from pydantic import BaseModel


class GameState(BaseModel):
    game_id: str
    status: str
    state: dict


class GameCreate(BaseModel):
    name: str | None = None


class GameJoin(BaseModel):
    player: str
    color: str | None = None


class GameStart(BaseModel):
    player: str
