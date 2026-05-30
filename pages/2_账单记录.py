from pathlib import Path

import streamlit as st

from config import BASE_DIR
from database import (
    get_all_players, get_bills_grouped_by_session,
    update_bill, delete_bill, delete_game_session,
)

IMAGES_DIR = BASE_DIR / "data" / "images"

st.set_page_config(page_title="账单记录", page_icon="📋", layout="wide")
st.title("📋 账单记录")

sessions = get_bills_grouped_by_session()
players = get_all_players()

if not sessions or all(len(s["bills"]) == 0 for s in sessions):
    st.info("暂无账单记录，请先上传截图。")
    st.stop()

# 筛选
col1, col2, col3 = st.columns(3)
with col1:
    player_filter = st.multiselect(
        "按玩家筛选",
        options=[p["name"] for p in players],
    )
with col2:
    date_range = st.date_input("按日期范围", value=())
with col3:
    sort_order = st.selectbox("排序", ["最新优先", "最早优先"], index=0)

# 应用筛选
filtered_sessions = []
for s in sessions:
    bills = s["bills"]
    if player_filter:
        bills = [b for b in bills if b["player_name"] in player_filter]
    if len(date_range) == 2:
        start, end = date_range[0].isoformat(), date_range[1].isoformat()
        bills = [b for b in bills if start <= b["game_date"] <= end]
    if bills:
        filtered_sessions.append({"session": s["session"], "bills": bills})

if sort_order == "最早优先":
    filtered_sessions = filtered_sessions[::-1]

total_bills = sum(len(s["bills"]) for s in filtered_sessions)
st.markdown(f"**共 {len(filtered_sessions)} 局，{total_bills} 条记录**")
st.markdown("---")

# 编辑模式
edit_mode = st.toggle("✏️ 开启编辑模式", value=False)

for s in filtered_sessions:
    sess = s["session"]
    bills = s["bills"]
    is_settled = bool(sess.get("settled"))
    ppp = sess.get("price_per_point", 5.0)

    # 标题：显示各玩家分数
    player_parts = []
    for b in bills:
        pts = b["win_points"]
        emoji = "🟢" if pts >= 0 else "🔴"
        label = f"{b['player_name']}{emoji}{pts:+.0f}分"
        if is_settled:
            label += f"(¥{pts * ppp:.0f})"
        player_parts.append(label)
    players_str = "  |  ".join(player_parts)

    time_str = f" {sess['game_time']}" if sess.get("game_time") else ""
    settled_str = f" ✅已结账 ¥{ppp}/分" if is_settled else ""
    header = f"🎲 {sess['game_date']}{time_str}{settled_str}  |  {players_str}"

    # 顶部便捷删除按钮
    c_header, c_del = st.columns([10, 1])
    with c_header:
        st.markdown(f"**{header}**")
    with c_del:
        if st.button("🗑️", key=f"del_top_{sess['id']}", help="删除整局"):
            delete_game_session(sess["id"])
            st.success("已删除整局记录")
            st.rerun()

    with st.expander("查看详情", expanded=False):
        # 图片
        if sess.get("image_path"):
            img_path = IMAGES_DIR / sess["image_path"]
            if img_path.exists():
                col_img, col_dl = st.columns([3, 1])
                with col_img:
                    st.image(str(img_path), caption="原始截图", use_container_width=True)
                with col_dl:
                    with open(img_path, "rb") as f:
                        st.download_button(
                            "📥 下载截图",
                            data=f,
                            file_name=sess["image_path"].split("_", 1)[-1] if "_" in sess["image_path"] else sess["image_path"],
                            mime="image/jpeg",
                            key=f"dl_{sess['id']}",
                        )

        for bill in bills:
            st.markdown("---")
            st.markdown(f"**{bill['player_name']}**")

            if edit_mode:
                player_names = {p["name"]: p["id"] for p in players}
                player_name_list = list(player_names.keys())

                c1, c2, c3 = st.columns([1, 1, 1])
                new_date = c1.date_input(
                    "日期",
                    value=__import__("datetime").date.fromisoformat(bill["game_date"]),
                    key=f"date_{bill['id']}",
                )
                current_idx = player_name_list.index(bill["player_name"]) if bill["player_name"] in player_names else 0
                new_player = c2.selectbox("玩家", player_name_list, index=current_idx, key=f"player_{bill['id']}")
                new_points = c3.number_input(
                    "分数", value=float(bill["win_points"]),
                    step=1.0, format="%.1f", key=f"pts_{bill['id']}",
                )

                c4, c5 = st.columns(2)
                new_lc = c4.number_input("地主次数", value=int(bill.get("landlord_count", 0)),
                                         min_value=0, step=1, key=f"lc_{bill['id']}")
                new_lw = c4.number_input("地主赢次", value=int(bill.get("landlord_win", 0)),
                                         min_value=0, step=1, key=f"lw_{bill['id']}")
                new_fc = c5.number_input("农民次数", value=int(bill.get("farmer_count", 0)),
                                         min_value=0, step=1, key=f"fc_{bill['id']}")
                new_fw = c5.number_input("农民赢次", value=int(bill.get("farmer_win", 0)),
                                         min_value=0, step=1, key=f"fw_{bill['id']}")
                new_remark = st.text_input("备注", value=bill["remark"], key=f"remark_{bill['id']}")

                ac1, ac2 = st.columns(2)
                if ac1.button("💾 保存", key=f"save_{bill['id']}"):
                    # 验证整局总分 = 0
                    total = sum(
                        new_points if b["id"] == bill["id"] else b["win_points"]
                        for b in bills
                    )
                    if abs(total) > 0.01:
                        st.error(f"❌ 保存失败：本局总分必须为 0，当前为 {total:+.0f}分，请检查其他玩家的分数。")
                    else:
                        update_bill(bill["id"], new_date.isoformat(), player_names[new_player],
                                    new_points, new_lc, new_lw, new_fc, new_fw, new_remark)
                        st.success("已更新")
                        st.rerun()
                if ac2.button("🗑️ 删除", key=f"del_{bill['id']}"):
                    delete_bill(bill["id"])
                    st.success("已删除")
                    st.rerun()
            else:
                cols = st.columns([1, 1, 1, 1])
                pts = bill["win_points"]
                emoji = "🟢" if pts >= 0 else "🔴"
                cols[0].markdown(f"💰 **分数**: {emoji} {pts:+.0f}分")
                if is_settled:
                    cols[0].markdown(f"💵 **金额**: ¥{pts * ppp:.2f}")

                lc = bill.get("landlord_count", 0)
                lw = bill.get("landlord_win", 0)
                fc = bill.get("farmer_count", 0)
                fw = bill.get("farmer_win", 0)
                l_rate = f"{lw/lc*100:.0f}%" if lc > 0 else "-"
                f_rate = f"{fw/fc*100:.0f}%" if fc > 0 else "-"

                if lc > 0 or fc > 0:
                    cols[1].markdown(f"👑 **地主**: {lc}次 胜{l_rate}")
                    cols[2].markdown(f"🌾 **农民**: {fc}次 胜{f_rate}")
                else:
                    cols[1].markdown("👑 **地主**: -")
                    cols[2].markdown("🌾 **农民**: -")

                cols[3].markdown(f"🕐 {bill['created_at']}")

                if bill["remark"]:
                    st.caption(f"📝 {bill['remark']}")
