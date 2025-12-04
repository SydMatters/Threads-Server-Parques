from fastapi import APIRouter, Depends, HTTPException, status

from app.deps import get_game_manager_dep
from app.schemas.game import GameCreate, GameState
from app.services.game_manager import GameManager

router = APIRouter()


@router.get("/", response_model=list[GameState])
def list_games(manager: GameManager = Depends(get_game_manager_dep)) -> list[GameState]:
    return [GameState(**session) for session in manager.list_games()]


@router.post("/", response_model=GameState, status_code=status.HTTP_201_CREATED)
def create_game(_: GameCreate, manager: GameManager = Depends(get_game_manager_dep)) -> GameState:
    session = manager.create_game()
    return GameState(**session.snapshot())


@router.get("/{game_id}", response_model=GameState)
def game_state(game_id: str, manager: GameManager = Depends(get_game_manager_dep)) -> GameState:
    try:
        session = manager.get_session(game_id)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game not found")
    return GameState(**session.snapshot())
