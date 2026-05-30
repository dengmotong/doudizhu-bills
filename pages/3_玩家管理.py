import streamlit as st

from database import get_all_players, add_player, delete_player, rename_player

st.set_page_config(page_title="玩家管理", page_icon="👥", layout="wide")
st.title("👥 玩家管理")

# 添加玩家
st.markdown("### ➕ 添加玩家")
col1, col2 = st.columns([3, 1])
with col1:
    new_name = st.text_input("玩家昵称", key="new_player_name")
with col2:
    st.write("")
    st.write("")
    if st.button("添加", type="primary"):
        if not new_name.strip():
            st.warning("请输入玩家昵称")
        else:
            try:
                add_player(new_name.strip())
                st.success(f"✅ 玩家 '{new_name.strip()}' 添加成功")
                st.rerun()
            except Exception as e:
                st.error(f"添加失败: {e}")

st.markdown("---")

# 玩家列表
players = get_all_players()
st.markdown(f"### 📋 玩家列表（共 {len(players)} 人）")

if not players:
    st.info("暂无玩家，请先添加。")
    st.stop()

for player in players:
    col1, col2, col3 = st.columns([3, 2, 1])
    with col1:
        st.write(f"**{player['name']}**")
    with col2:
        st.caption(f"ID: {player['id']} | 创建时间: {player['created_at']}")
    with col3:
        if st.button("🗑️ 删除", key=f"del_{player['id']}"):
            delete_player(player["id"])
            st.success(f"已删除 {player['name']}")
            st.rerun()

# 重命名
st.markdown("---")
st.markdown("### ✏️ 重命名玩家")
if players:
    player_names = [p["name"] for p in players]
    selected = st.selectbox("选择玩家", player_names)
    new_name = st.text_input("新昵称", key="rename_player_name")
    if st.button("重命名"):
        if not new_name.strip():
            st.warning("请输入新昵称")
        else:
            player_id = next(p["id"] for p in players if p["name"] == selected)
            rename_player(player_id, new_name.strip())
            st.success(f"✅ 已将 '{selected}' 重命名为 '{new_name.strip()}'")
            st.rerun()
