import json
import re
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from io import BytesIO

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from PIL import Image

from .. import database
from ..config import IMAGES_DIR
from ..llm import apply_win_rates, recognize_bill
from ..utils import merge_duplicate_players, validate_session_zero

router = APIRouter(prefix="/api", tags=["recognize"])


def parse_filename_datetime(filename: str) -> tuple[str | None, str]:
    """从文件名中解析日期与时间（形如 2024-01-15-14-30-00）。"""
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})-(\d{2})-(\d{2})-(\d{2})", filename)
    if m:
        y, mo, d, h, mi, s = int(m[1]), int(m[2]), int(m[3]), int(m[4]), int(m[5]), int(m[6])
        try:
            return date(y, mo, d).isoformat(), f"{h:02d}:{mi:02d}"
        except ValueError:
            pass
    return None, ""


@router.post("/recognize")
async def recognize(
    files: list[UploadFile] = File(...),
    api_key: str = Form(""),
    base_url: str = Form(""),
    model: str = Form(""),
):
    """批量识别结算截图，返回结构化结果（不落库）。

    使用 OpenAI 兼容 API 并发识别，最多同时处理 5 张。
    """
    # 读取文件数据到内存
    file_data = []
    for f in files:
        data = await f.read()
        file_data.append((f.filename or "unknown", data))

    player_names = [p["name"] for p in database.get_all_players()]

    def recognize_one(filename: str, buf: bytes) -> dict:
        try:
            image = Image.open(BytesIO(buf))
            result = recognize_bill(
                image,
                api_key=api_key,
                base_url=base_url,
                model=model,
                player_names=player_names,
            )
            fn_date, fn_time = parse_filename_datetime(filename)
            return {
                "file_name": filename,
                "status": "done",
                "result": result,
                "fn_date": fn_date,
                "fn_time": fn_time,
                "error": None,
            }
        except Exception as e:  # noqa: BLE001
            return {
                "file_name": filename,
                "status": "error",
                "result": None,
                "fn_date": None,
                "fn_time": "",
                "error": str(e),
            }

    results = []
    with ThreadPoolExecutor(max_workers=min(len(file_data), 5)) as executor:
        futures = [
            executor.submit(recognize_one, filename, buf)
            for filename, buf in file_data
        ]
        for fut in as_completed(futures):
            results.append(fut.result())

    return {"results": results}


@router.post("/sessions/batch")
async def save_sessions(
    files: list[UploadFile] = File(...),
    payload: str = Form(...),
):
    """批量保存：写入截图文件 + 创建会话 + 写入账单。payload 为 JSON 字符串列表。

    payload 每项形如：
    {
        "file_name": "a.png",
        "game_date": "2024-01-15",
        "game_time": "14:30",
        "raw_text": "...",
        "players": [{"name": "x", "win_points": 5, "landlord_count": 0, ...}, ...]
    }
    """
    try:
        items = json.loads(payload)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="payload 不是合法 JSON")

    file_map = {f.filename or "": f for f in files}
    player_id_map = {p["name"]: p["id"] for p in database.get_all_players()}

    saved = []
    for item in items:
        uf = file_map.get(item.get("file_name"))
        if not uf:
            raise HTTPException(status_code=400, detail=f"未找到文件 {item.get('file_name')}")

        # 胜负盘数一律由「盘数 × 胜率」在本地计算，不采信前端/模型传来的赢次
        apply_win_rates(item)
        players = merge_duplicate_players(item.get("players", []))
        is_valid, total = validate_session_zero(players)
        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail=f"{item.get('file_name')} 总分必须为 0，当前为 {total:+.0f} 分",
            )

        # 保存图片
        content = await uf.read()
        saved_filename = f"{uuid.uuid4().hex[:8]}_{uf.filename}"
        with open(IMAGES_DIR / saved_filename, "wb") as fh:
            fh.write(content)

        # 确保玩家存在
        for p in players:
            if p["name"] not in player_id_map:
                new_id = database.add_player(p["name"])
                player_id_map[p["name"]] = new_id

        session_id = database.add_game_session(
            game_date=item.get("game_date") or date.today().isoformat(),
            game_time=item.get("game_time", ""),
            image_path=saved_filename,
            raw_text=item.get("raw_text", ""),
        )

        database.add_bills([
            {
                "game_session_id": session_id,
                "game_date": item.get("game_date") or date.today().isoformat(),
                "player_id": player_id_map[p["name"]],
                "win_points": p.get("win_points", 0),
                "landlord_count": p.get("landlord_count", 0),
                "landlord_win": p.get("landlord_win", 0),
                "farmer_count": p.get("farmer_count", 0),
                "farmer_win": p.get("farmer_win", 0),
                "remark": p.get("remark", ""),
            }
            for p in players
        ])
        saved.append({"file_name": item.get("file_name"), "session_id": session_id})

    return {"saved": saved}
