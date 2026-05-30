from pathlib import Path

import streamlit as st

from config import BASE_DIR
from database import (
    get_all_game_sessions, get_session_bills,
    settle_game_session, unsettle_game_session,
)

IMAGES_DIR = BASE_DIR / "data" / "images"

st.set_page_config(page_title="结账", page_icon="💰", layout="wide")
st.title("💰 结账")


def calculate_settlement(bills: list[dict], price_per_point: float = 5.0) -> list[dict]:
    """
    计算最优结账策略（最少转账次数）。
    bills 中使用 win_points，返回金额。
    """
    scores = {}
    for b in bills:
        name = b["player_name"]
        scores[name] = scores.get(name, 0) + b["win_points"]

    scores = {k: round(v, 2) for k, v in scores.items() if abs(v) > 0.001}

    winners = sorted([(k, v) for k, v in scores.items() if v > 0], key=lambda x: x[1], reverse=True)
    losers = sorted([(k, -v) for k, v in scores.items() if v < 0], key=lambda x: x[1], reverse=True)

    transfers = []
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


def get_scores(bills: list[dict]) -> dict[str, float]:
    scores = {}
    for b in bills:
        name = b["player_name"]
        scores[name] = scores.get(name, 0) + b["win_points"]
    return {k: round(v, 2) for k, v in scores.items() if abs(v) > 0.001}


# 获取所有对局（只显示有账单的）
sessions = get_all_game_sessions()
sessions_with_bills = []
for s in sessions:
    bills = get_session_bills(s["id"])
    if bills:
        sessions_with_bills.append((s, bills))

if not sessions_with_bills:
    st.info("暂无对局记录。")
    st.stop()

unsettled = [(s, b) for s, b in sessions_with_bills if not s.get("settled")]
settled = [(s, b) for s, b in sessions_with_bills if s.get("settled")]

# ---- 未结账 ----
st.markdown("### ⏳ 待结账对局")

if not unsettled:
    st.info("没有待结账的对局。")
else:
    # 批量选择
    batch_ids = st.multiselect(
        "选择要结账的对局（可多选，合并计算）",
        options=[s["id"] for s, _ in unsettled],
        format_func=lambda sid: next(
            f"{s['game_date']} {s.get('game_time', '')} (ID:{s['id']})"
            for s, _ in unsettled if s["id"] == sid
        ),
        key="batch_select",
    )

    default_ppp = st.number_input("每分单价（元）", value=5.0, min_value=0.1, step=0.5, key="default_ppp")

    if batch_ids:
        all_bills = []
        for sid in batch_ids:
            all_bills.extend(next(b for s, b in unsettled if s["id"] == sid))

        scores = get_scores(all_bills)
        transfers = calculate_settlement(all_bills, default_ppp)

        st.markdown("#### 📊 合并结账计算")
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**各玩家总分数：**")
            for name, pts in sorted(scores.items(), key=lambda x: x[1], reverse=True):
                emoji = "🟢" if pts >= 0 else "🔴"
                money = pts * default_ppp
                st.markdown(f"- {name}: {emoji} **{pts:+.0f}分** (¥{money:.2f})")

        with col2:
            st.markdown("**最优转账方案：**")
            if transfers:
                for t in transfers:
                    st.markdown(
                        f"- 💸 **{t['from']}** → **{t['to']}**  "
                        f"**{t['points']:.0f}分** (¥{t['money']:.2f})"
                    )
                st.caption(f"共 {len(transfers)} 笔转账，每分 ¥{default_ppp}")
            else:
                st.info("所有人分数相同，无需转账")

        if st.button("✅ 确认批量结账", type="primary", key="batch_settle"):
            for sid in batch_ids:
                settle_game_session(sid, default_ppp)
            st.success(f"✅ 已结账 {len(batch_ids)} 局")
            st.rerun()

    st.markdown("---")

    # 逐局
    for s, bills in unsettled:
        scores = get_scores(bills)
        ppp = default_ppp
        transfers = calculate_settlement(bills, ppp)

        players_summary = " | ".join(
            f"{b['player_name']}{'🟢' if b['win_points'] >= 0 else '🔴'}{b['win_points']:+.0f}分"
            for b in bills
        )

        with st.expander(f"🎲 {s['game_date']} {s.get('game_time', '')}  |  {players_summary}"):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**各玩家分数：**")
                for name, pts in sorted(scores.items(), key=lambda x: x[1], reverse=True):
                    emoji = "🟢" if pts >= 0 else "🔴"
                    st.markdown(f"- {name}: {emoji} **{pts:+.0f}分** (¥{pts * ppp:.2f})")

            with col2:
                st.markdown("**转账方案：**")
                if transfers:
                    for t in transfers:
                        st.markdown(
                            f"- 💸 **{t['from']}** → **{t['to']}**  "
                            f"**{t['points']:.0f}分** (¥{t['money']:.2f})"
                        )
                else:
                    st.info("所有人分数相同，无需转账")

            if s.get("image_path"):
                img_path = IMAGES_DIR / s["image_path"]
                if img_path.exists():
                    st.image(str(img_path), caption="原始截图", use_container_width=True)

            if st.button("✅ 结账", key=f"settle_{s['id']}"):
                settle_game_session(s["id"], ppp)
                st.success("✅ 已结账")
                st.rerun()

# ---- 已结账 ----
if settled:
    st.markdown("---")
    st.markdown(f"### ✅ 已结账对局（{len(settled)} 局）")

    for s, bills in settled:
        ppp = s.get("price_per_point", 5.0)
        scores = get_scores(bills)
        transfers = calculate_settlement(bills, ppp)

        players_summary = " | ".join(
            f"{b['player_name']}{'🟢' if b['win_points'] >= 0 else '🔴'}"
            f"{b['win_points']:+.0f}分(¥{b['win_points'] * ppp:.0f})"
            for b in bills
        )

        with st.expander(f"✅ {s['game_date']} {s.get('game_time', '')} ¥{ppp}/分  |  {players_summary}"):
            col1, col2 = st.columns([3, 1])
            with col1:
                if transfers:
                    for t in transfers:
                        st.markdown(
                            f"- 💸 {t['from']} → {t['to']}  "
                            f"{t['points']:.0f}分 (¥{t['money']:.2f})"
                        )
                st.caption(f"结账时间: {s.get('settled_at', '-')}  |  单价: ¥{ppp}/分")
            with col2:
                if st.button("↩️ 取消结账", key=f"unsettle_{s['id']}"):
                    unsettle_game_session(s["id"])
                    st.success("已取消结账")
                    st.rerun()
