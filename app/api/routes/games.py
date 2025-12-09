import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.deps import get_game_manager_dep
from app.schemas.actions import MoveRequest, MoveResponse
from app.schemas.game import GameCreate, GameState, GameJoin, GameStart
from app.services.game_manager import GameManager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=GameState, status_code=status.HTTP_201_CREATED)
def create_game(_: GameCreate, manager: GameManager = Depends(get_game_manager_dep)) -> GameState:
  session = manager.create_game()
  logger.info("Create game requested")
  return GameState(**session.snapshot())


@router.post("/join", response_model=GameState)
def join_game(payload: GameJoin, manager: GameManager = Depends(get_game_manager_dep)) -> GameState:
  try:
    logger.info("Join request: %s", payload.dict())
    session = manager.join_game(player_name=payload.player, color_name=payload.color)
  except ValueError as exc:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
  return GameState(**session.snapshot())


@router.post("/start", response_model=GameState)
def start_game(payload: GameStart, manager: GameManager = Depends(get_game_manager_dep)) -> GameState:
  try:
    session = manager.start_game(started_by=payload.player)
  except ValueError as exc:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
  return GameState(**session.snapshot())


@router.post("/move", response_model=MoveResponse)
def move_token(payload: MoveRequest, manager: GameManager = Depends(get_game_manager_dep)) -> MoveResponse:
  try:
    logger.info("Move request: %s", payload.dict())
    result = manager.move_token(player_name=payload.player, token_id=payload.token_id, steps=payload.steps)
  except ValueError as exc:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
  return result  # matches MoveResponse
