from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.deps import get_db
from app.schemas.player import PlayerCreate, PlayerRead
from database.players import Player

router = APIRouter()


@router.post("/", response_model=PlayerRead, status_code=status.HTTP_201_CREATED)
def create_player(payload: PlayerCreate, db: Session = Depends(get_db)) -> Player:
    existing = db.query(Player).filter(Player.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Player already exists")
    player = Player(name=payload.name, age=payload.age, password=payload.password, score=0)
    db.add(player)
    db.commit()
    db.refresh(player)
    return player


@router.get("/", response_model=list[PlayerRead])
def list_players(db: Session = Depends(get_db)) -> list[Player]:
    return db.query(Player).all()


@router.get("/{player_id}", response_model=PlayerRead)
def get_player(player_id: int, db: Session = Depends(get_db)) -> Player:
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Player not found")
    return player
