"""结账计算：基于每分单价，给出最少转账次数的结算方案。"""


def get_scores(bills: list[dict]) -> dict[str, float]:
    """汇总每个玩家的总分数（忽略接近零的玩家）。"""
    scores: dict[str, float] = {}
    for b in bills:
        name = b["player_name"]
        scores[name] = scores.get(name, 0) + b["win_points"]
    return {k: round(v, 2) for k, v in scores.items() if abs(v) > 0.001}


def calculate_settlement(bills: list[dict], price_per_point: float = 5.0) -> list[dict]:
    """计算最优结账策略（最少转账次数）。

    bills 中使用 win_points，返回金额。
    贪心算法：从最大赢家与最大输家配对，一次转账满足一方。
    """
    scores = get_scores(bills)

    # 赢家按金额降序，输家按金额降序（转正处理）
    winners = sorted([(k, v) for k, v in scores.items() if v > 0], key=lambda x: x[1], reverse=True)
    losers = sorted([(k, -v) for k, v in scores.items() if v < 0], key=lambda x: x[1], reverse=True)

    transfers: list[dict] = []
    wi, li = 0, 0
    while wi < len(winners) and li < len(losers):
        w_name, w_pts = winners[wi]
        l_name, l_pts = losers[li]

        transfer_pts = min(w_pts, l_pts)
        if transfer_pts > 0.001:
            transfers.append({
                "from": l_name,
                "to": w_name,
                "points": round(transfer_pts, 2),
                "money": round(transfer_pts * price_per_point, 2),
            })

        winners[wi] = (w_name, w_pts - transfer_pts)
        losers[li] = (l_name, l_pts - transfer_pts)

        if winners[wi][1] < 0.001:
            wi += 1
        if losers[li][1] < 0.001:
            li += 1

    return transfers
