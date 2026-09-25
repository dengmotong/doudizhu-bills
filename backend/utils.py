"""纯业务逻辑辅助函数（无 IO）。"""


def merge_duplicate_players(players: list[dict]) -> list[dict]:
    """同一结算单内合并同名列的玩家，累加其分数与对局字段。"""
    seen: dict[str, dict] = {}
    for p in players:
        name = p.get("name", "")
        if not name:
            continue
        if name in seen:
            seen[name]["win_points"] = seen[name].get("win_points", 0) + p.get("win_points", 0)
            seen[name]["landlord_count"] = seen[name].get("landlord_count", 0) + p.get("landlord_count", 0)
            seen[name]["landlord_win"] = seen[name].get("landlord_win", 0) + p.get("landlord_win", 0)
            seen[name]["farmer_count"] = seen[name].get("farmer_count", 0) + p.get("farmer_count", 0)
            seen[name]["farmer_win"] = seen[name].get("farmer_win", 0) + p.get("farmer_win", 0)
        else:
            seen[name] = dict(p)
    return list(seen.values())


def validate_session_zero(players: list[dict]) -> tuple[bool, float]:
    """校验一局总分是否为 0（误差 < 0.01）。返回 (是否合法, 总分)。"""
    total = sum(p.get("win_points", 0) for p in players)
    return abs(total) < 0.01, total
