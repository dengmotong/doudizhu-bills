import streamlit as st

st.set_page_config(
    page_title="斗地主账单",
    page_icon="🃏",
    layout="wide",
)

st.title("🃏 斗地主账单系统")
st.markdown("---")

st.markdown("""
### 功能导航

👈 请使用左侧边栏切换功能页面：

- **📤 账单上传** — 上传斗地主结算截图，AI 自动识别输赢
- **📋 账单记录** — 查看、编辑、删除历史账单
- **👥 玩家管理** — 管理玩家信息
- **📊 统计分析** — 多维度统计输赢，图表可视化
- **💰 结账** — 选择对局计算最优转账方案，标记已结账
""")

st.markdown("---")

# 显示概览数据
from database import get_all_bills, get_all_players

players = get_all_players()
bills = get_all_bills()

col1, col2, col3 = st.columns(3)
col1.metric("👥 玩家总数", len(players))
col2.metric("📋 账单总数", len(bills))

if bills:
    total = sum(b["win_points"] for b in bills)
    col3.metric("📊 总分数", f"{total:+.0f}")
else:
    col3.metric("📊 总分数", "0")

if bills:
    st.markdown("### 🏆 当前排名")
    stats = {}
    for b in bills:
        name = b["player_name"]
        stats[name] = stats.get(name, 0) + b["win_points"]

    sorted_stats = sorted(stats.items(), key=lambda x: x[1], reverse=True)
    for i, (name, amount) in enumerate(sorted_stats):
        emoji = ["🥇", "🥈", "🥉"][i] if i < 3 else "  "
        color = "green" if amount >= 0 else "red"
        st.markdown(f"{emoji} **{name}**: :{color}[{amount:+.0f}分]")
