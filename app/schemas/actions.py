from pydantic import BaseModel


class RollRequest(BaseModel):
    player: str


class RollResponse(BaseModel):
    dice: list[int]
    state: dict


class MoveRequest(BaseModel):
    player: str
    token_id: int
    steps: int | None = None


class MoveResponse(BaseModel):
    state: dict
