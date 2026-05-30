import re
import uuid
from datetime import date
from pathlib import Path

import streamlit as st
from PIL import Image

from config import BASE_DIR
from database import get_all_players, add_player, add_bills, add_game_session
from llm import recognize_bill

IMAGES_DIR = BASE_DIR / "data" / "images"
IMAGES_DIR.mkdir(parents=True, exist_ok=True)


def parse_filename_datetime(filename: str) -> tuple[date | None, str]:
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})-(\d{2})-(\d{2})-(\d{2})", filename)
    if m:
        y, mo, d, h, mi, s = int(m[1]), int(m[2]), int(m[3]), int(m[4]), int(m[5]), int(m[6])
        try:
            return date(y, mo, d), f"{h:02d}:{mi:02d}"
        except ValueError:
            pass
    return None, ""


def validate_session_zero(players: list[dict]) -> tuple[bool, float]:
    total = sum(p.get("win_points", 0) for p in players)
    return abs(total) < 0.01, total


def save_one_result(uploaded_file, result, edited_players, game_date, game_time, player_id_map):
    for p in edited_players:
        if p["name"] not in player_id_map:
            new_id = add_player(p["name"])
            player_id_map[p["name"]] = new_id

    saved_filename = f"{uuid.uuid4().hex[:8]}_{uploaded_file.name}"
    saved_path = IMAGES_DIR / saved_filename
    uploaded_file.seek(0)
    with open(saved_path, "wb") as f:
        f.write(uploaded_file.read())

    session_id = add_game_session(
        game_date=game_date.isoformat(),
        game_time=game_time,
        image_path=saved_filename,
        raw_text=str(result),
    )

    add_bills([
        {
            "game_session_id": session_id,
            "game_date": game_date.isoformat(),
            "player_id": player_id_map[p["name"]],
            "win_points": p["win_points"],
            "landlord_count": p["landlord_count"],
            "landlord_win": p["landlord_win"],
            "farmer_count": p["farmer_count"],
            "farmer_win": p["farmer_win"],
            "remark": "",
        }
        for p in edited_players
    ])
    return session_id


# ========== 页面 ==========

st.set_page_config(page_title="账单上传", page_icon="📤", layout="wide")
st.title("📤 账单上传")

# API 配置
with st.expander("⚙️ API 配置", expanded=not bool(__import__("os").environ.get("OPENAI_API_KEY", ""))):
    api_key = st.text_input(
        "API Key",
        value=st.session_state.get("api_key", ""),
        type="password",
        help="API 密钥",
    )
    if api_key:
        st.session_state["api_key"] = api_key

    base_url = st.text_input(
        "Base URL",
        value=st.session_state.get("base_url", ""),
        placeholder="https://api.example.com/v1",
        help="API 地址，例如 https://api.mimo.xxx/v1",
    )
    if base_url:
        st.session_state["base_url"] = base_url

    model = st.text_input(
        "模型名",
        value=st.session_state.get("model", ""),
        placeholder="mimo-v2-omni",
        help="多模态模型名称",
    )
    if model:
        st.session_state["model"] = model

st.markdown("---")

# 上传截图（支持多张）
uploaded_files = st.file_uploader(
    "上传斗地主结算截图（可多选）",
    type=["png", "jpg", "jpeg", "webp"],
    accept_multiple_files=True,
    help="支持一次选择多张截图批量上传",
)

if not uploaded_files:
    st.stop()

file_map = {uf.name: uf for uf in uploaded_files}

# 初始化 batch_items
if "batch_items" not in st.session_state:
    st.session_state["batch_items"] = []

existing_names = {item["file_name"] for item in st.session_state["batch_items"]}
for uf in uploaded_files:
    if uf.name not in existing_names:
        st.session_state["batch_items"].append({
            "file_name": uf.name,
            "status": "pending",  # pending / recognizing / done / error / saved
            "result": None,
            "fn_date": None,
            "fn_time": "",
            "error": None,
        })

current_names = {uf.name for uf in uploaded_files}
st.session_state["batch_items"] = [
    item for item in st.session_state["batch_items"]
    if item["file_name"] in current_names
]

items = st.session_state["batch_items"]
pending_items = [i for i in items if i["status"] == "pending"]
recognizing_items = [i for i in items if i["status"] == "recognizing"]

# ========== 识别管线（UI 之前，不阻塞渲染）==========
status_box = st.empty()

if recognizing_items:
    item = recognizing_items[0]
    uf = file_map.get(item["file_name"])
    if uf:
        status_box.info(f"🤖 正在识别: {item['file_name']} ...")
        try:
            image = Image.open(uf)
            result = recognize_bill(
                image,
                api_key=st.session_state.get("api_key", ""),
                base_url=st.session_state.get("base_url", ""),
                model=st.session_state.get("model", ""),
            )
            item["result"] = result
            item["fn_date"], item["fn_time"] = parse_filename_datetime(uf.name)
            item["status"] = "done"
        except Exception as e:
            item["error"] = str(e)
            item["status"] = "error"
        status_box.empty()
        st.rerun()

# ========== UI 渲染（始终渲染，不受识别阻塞）==========

# 进度提示
done_count = sum(1 for i in items if i["status"] in ("done", "saved"))
error_count = sum(1 for i in items if i["status"] == "error")
rec_count = sum(1 for i in items if i["status"] == "recognizing")
pending_count = len(pending_items)

if pending_count > 0 or rec_count > 0:
    st.info(f"📊 进度: {done_count} 已识别  |  {rec_count} 识别中  |  {pending_count} 待识别  |  {error_count} 失败")

# 预览区
st.markdown(f"### 📷 已上传 {len(uploaded_files)} 张截图")
cols = st.columns(min(len(uploaded_files), 4))
for i, uf in enumerate(uploaded_files):
    with cols[i % 4]:
        st.image(Image.open(uf), caption=uf.name, use_container_width=True)

# 识别按钮
if pending_items:
    if st.button(f"🔍 开始识别全部（{len(pending_items)} 张待识别）", type="primary"):
        for item in pending_items:
            item["status"] = "recognizing"
        st.rerun()

st.markdown("---")

# 编辑区
players = get_all_players()
player_id_map = {p["name"]: p["id"] for p in players}
player_name_list = [p["name"] for p in players]

# 错误项
for item in items:
    if item["status"] == "error":
        st.error(f"❌ **{item['file_name']}** 识别失败: {item['error']}")
        idx = items.index(item)
        if st.button("🔄 重试", key=f"retry_{idx}"):
            item["status"] = "pending"
            item["error"] = None
            st.rerun()

# 已完成的编辑区
for idx, item in enumerate(items):
    if item["status"] != "done":
        continue

    uf = file_map.get(item["file_name"])
    if not uf:
        continue

    result = item["result"]
    players_summary = ", ".join(
        f"{p['name']}{'🟢' if p.get('win_points', 0) >= 0 else '🔴'}{p.get('win_points', 0):+.0f}"
        for p in result["players"]
    )

    with st.expander(f"🎲 [{idx+1}] {item['file_name']}  —  {players_summary}", expanded=False):
        col_img, col_edit = st.columns([1, 1])

        with col_img:
            st.image(Image.open(uf), caption=uf.name, use_container_width=True)

        with col_edit:
            game_date = item["fn_date"] if item["fn_date"] else date.today()
            game_time = item["fn_time"]
            c1, c2 = st.columns(2)
            game_date = c1.date_input("游戏日期", value=game_date, key=f"date_{idx}")
            game_time = c2.text_input("游戏时间", value=game_time, placeholder="HH:MM", key=f"time_{idx}")

            options = player_name_list + ["➕ 新增玩家"]
            for pi, p in enumerate(result["players"]):
                st.markdown(f"**{p['name']}**")
                ca, cb, cc = st.columns([2, 1, 1])

                match_idx = 0
                for i, pn in enumerate(player_name_list):
                    if pn == p["name"]:
                        match_idx = i
                        break

                selected = ca.selectbox("玩家", options, index=match_idx, key=f"pl_{idx}_{pi}")
                if selected == "➕ 新增玩家":
                    new_name = cb.text_input("新昵称", value=p["name"], key=f"nn_{idx}_{pi}")
                    actual_name = new_name
                else:
                    actual_name = selected
                    cc.success("✅")

                p["win_points"] = cb.number_input(
                    "输赢分数",
                    value=float(p.get("win_points", p.get("win_amount", 0))),
                    step=1.0, format="%.1f",
                    key=f"pts_{idx}_{pi}",
                )
                p["landlord_count"] = st.number_input("地主次数", value=int(p.get("landlord_count", 0)), min_value=0, step=1, key=f"lc_{idx}_{pi}")
                p["landlord_win"] = st.number_input("地主赢次", value=int(p.get("landlord_win", 0)), min_value=0, step=1, key=f"lw_{idx}_{pi}")
                p["farmer_count"] = st.number_input("农民次数", value=int(p.get("farmer_count", 0)), min_value=0, step=1, key=f"fc_{idx}_{pi}")
                p["farmer_win"] = st.number_input("农民赢次", value=int(p.get("farmer_win", 0)), min_value=0, step=1, key=f"fw_{idx}_{pi}")
                p["name"] = actual_name

        if st.button("💾 保存此条", key=f"save_{idx}", type="primary"):
            is_valid, total = validate_session_zero(result["players"])
            if not is_valid:
                st.error(f"❌ 总分必须为 0，当前为 {total:+.0f}分，请检查。")
            else:
                save_one_result(uf, result, result["players"], game_date, game_time, player_id_map)
                item["status"] = "saved"
                st.success(f"✅ {uf.name} 已保存")
                st.rerun()

    st.markdown("---")

# 已保存
for item in items:
    if item["status"] == "saved":
        st.success(f"✅ {item['file_name']} 已保存")

# 批量保存
unsaved = [i for i in items if i["status"] == "done"]
if unsaved:
    st.markdown(f"**还有 {len(unsaved)} 条待保存**")
    if st.button("💾 一键保存全部待识别结果", type="primary"):
        to_save = []
        has_error = False
        for idx, item in enumerate(items):
            if item["status"] != "done":
                continue
            uf = file_map.get(item["file_name"])
            if not uf:
                continue
            gd = st.session_state.get(f"date_{idx}", item["fn_date"] or date.today())
            gt = st.session_state.get(f"time_{idx}", item["fn_time"])
            result = item["result"]
            for pi, p in enumerate(result["players"]):
                p["win_points"] = st.session_state.get(f"pts_{idx}_{pi}", p.get("win_points", 0))
                p["landlord_count"] = st.session_state.get(f"lc_{idx}_{pi}", 0)
                p["landlord_win"] = st.session_state.get(f"lw_{idx}_{pi}", 0)
                p["farmer_count"] = st.session_state.get(f"fc_{idx}_{pi}", 0)
                p["farmer_win"] = st.session_state.get(f"fw_{idx}_{pi}", 0)
                p["name"] = st.session_state.get(f"pl_{idx}_{pi}", p["name"])
                nn = st.session_state.get(f"nn_{idx}_{pi}", "")
                if nn:
                    p["name"] = nn
            is_valid, total = validate_session_zero(result["players"])
            if not is_valid:
                st.error(f"❌ 第 {idx+1} 张 ({item['file_name']}) 总分不为 0: {total:+.0f}分，请先修正。")
                has_error = True
            else:
                to_save.append((uf, result, result["players"], gd, gt))

        if not has_error:
            saved_count = 0
            for uf, result, players, gd, gt in to_save:
                save_one_result(uf, result, players, gd, gt, player_id_map)
                saved_count += 1
            for item in items:
                if item["status"] == "done":
                    item["status"] = "saved"
            st.success(f"✅ 已批量保存 {saved_count} 条记录！")
            st.rerun()
