from fastapi import APIRouter, HTTPException

from .. import database
from ..schemas import PlayerCreate, PlayerRename

router = APIRouter(prefix="/api/players", tags=["players"])


@router.get("")
def list_players():
    return database.get_all_players()


@router.post("")
def create_player(body: PlayerCreate):
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="玩家昵称不能为空")
    exists = [p for p in database.get_all_players() if p["name"] == name]
    if exists:
        raise HTTPException(status_code=400, detail=f"玩家 '{name}' 已存在")
    pid = database.add_player(name)
    return {"id": pid, "name": name}


@router.put("/{player_id}")
def rename_player(player_id: int, body: PlayerRename):
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="玩家昵称不能为空")
    database.rename_player(player_id, name)
    return {"ok": True}


@router.delete("/{player_id}")
def delete_player(player_id: int):
    database.delete_player(player_id)
    return {"ok": True}
