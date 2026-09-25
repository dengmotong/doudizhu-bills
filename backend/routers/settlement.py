from fastapi import APIRouter, HTTPException

from .. import database
from ..schemas import SettleBatchRequest, SettleSingleRequest, SettlementRequest
from ..settlement import calculate_settlement, get_scores

router = APIRouter(prefix="/api", tags=["settlement"])


def _collect_bills(session_ids: list[int]) -> list[dict]:
    bills: list[dict] = []
    for sid in session_ids:
        b = database.get_session_bills(sid)
        if not b:
            raise HTTPException(status_code=404, detail=f"对局 {sid} 不存在或无账单")
        bills.extend(b)
    return bills


@router.post("/settlement/transfers")
def compute_transfers(body: SettlementRequest):
    """对所选对局合并计算各玩家总分数与最优转账方案。"""
    if not body.session_ids:
        raise HTTPException(status_code=400, detail="请选择至少一个对局")
    bills = _collect_bills(body.session_ids)
    scores = get_scores(bills)
    transfers = calculate_settlement(bills, body.price_per_point)
    return {
        "scores": scores,
        "transfers": transfers,
        "price_per_point": body.price_per_point,
    }


@router.post("/sessions/{session_id}/settle")
def settle(session_id: int, body: SettleSingleRequest):
    database.settle_game_session(session_id, body.price_per_point)
    return {"ok": True}


@router.post("/sessions/{session_id}/unsettle")
def unsettle(session_id: int):
    database.unsettle_game_session(session_id)
    return {"ok": True}


@router.post("/settlement/batch-settle")
def batch_settle(body: SettleBatchRequest):
    if not body.session_ids:
        raise HTTPException(status_code=400, detail="请选择至少一个对局")
    for sid in body.session_ids:
        database.settle_game_session(sid, body.price_per_point)
    return {"ok": True, "count": len(body.session_ids)}
