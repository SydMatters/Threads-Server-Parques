from pydantic import BaseModel


class PlayerBase(BaseModel):
    name: str
    age: int | None = None


class PlayerCreate(PlayerBase):
    password: str


class PlayerRead(PlayerBase):
    id: int
    score: int | None = 0

    class Config:
        orm_mode = True
