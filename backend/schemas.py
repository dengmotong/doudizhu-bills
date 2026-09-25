"""Pydantic 请求/响应模型。"""
from typing import Optional

from pydantic import BaseModel, Field


# ---- Players ----

class PlayerCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)


class PlayerRename(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)


# ---- Bills ----

class BillInput(BaseModel):
    player_id: int
    win_points: float = 0
    landlord_count: int = 0
    landlord_win: int = 0
    farmer_count: int = 0
    farmer_win: int = 0
    remark: str = ""


class BillUpdate(BaseModel):
    player_id: int
    game_date: str
    win_points: float = 0
    landlord_count: int = 0
    landlord_win: int = 0
    farmer_count: int = 0
    farmer_win: int = 0
    remark: str = ""


class BatchSessionItem(BaseModel):
    """单张截图对应的保存信息（配合 files 上传）。"""
    file_name: str
    game_date: str
    game_time: str = ""
    raw_text: str = ""
    players: list[BillInput] = []


# ---- 识别配置 ----

class RecognizeConfig(BaseModel):
    api_key: str = ""
    base_url: str = ""
    model: str = ""


# ---- 结账 ----

class SettlementRequest(BaseModel):
    session_ids: list[int] = []
    price_per_point: float = 5.0


class SettleBatchRequest(BaseModel):
    session_ids: list[int] = []
    price_per_point: float = 5.0


class SettleSingleRequest(BaseModel):
    price_per_point: float = 5.0
