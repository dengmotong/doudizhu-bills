from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from .. import database
from ..config import IMAGES_DIR
from ..schemas import BillUpdate

router = APIRouter(prefix="/api", tags=["bills"])


@router.get("/sessions")
def list_sessions():
    """按局分组返回所有账单（含零散账单）。"""
    return database.get_bills_grouped_by_session()


@router.get("/bills")
def list_bills():
    return database.get_all_bills()


@router.delete("/sessions/{session_id}")
def delete_session(session_id: int):
    database.delete_game_session(session_id)
    return {"ok": True}


@router.put("/bills/{bill_id}")
def update_bill(bill_id: int, body: BillUpdate):
    database.update_bill(
        bill_id,
        game_date=body.game_date,
        player_id=body.player_id,
        win_points=body.win_points,
        landlord_count=body.landlord_count,
        landlord_win=body.landlord_win,
        farmer_count=body.farmer_count,
        farmer_win=body.farmer_win,
        remark=body.remark,
    )
    return {"ok": True}


@router.delete("/bills/{bill_id}")
def delete_bill(bill_id: int):
    database.delete_bill(bill_id)
    return {"ok": True}


@router.get("/images/{filename}")
def serve_image(filename: str):
    """提供已保存的结算截图。"""
    base = IMAGES_DIR.resolve()
    target = (IMAGES_DIR / filename).resolve()
    if not target.is_relative_to(base) or not target.is_file():
        raise HTTPException(status_code=404, detail="图片不存在")
    return FileResponse(target)
