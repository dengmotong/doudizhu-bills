import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from database import (
    get_player_cumulative_stats,
    get_player_stats_by_month,
    get_player_stats_by_day,
    get_player_stats_by_session,
)

st.set_page_config(page_title="统计分析", page_icon="📊", layout="wide")
st.title("📊 统计分析")

stats = get_player_cumulative_stats()
if not stats:
    st.info("暂无数据，请先上传账单。")
    st.stop()

strategy = st.selectbox(
    "📈 选择统计策略",
    ["累计排名", "按月统计", "按日统计", "按局统计"],
)

st.markdown("---")

# ---- 累计排名 ----
if strategy == "累计排名":
    df = pd.DataFrame(stats)

    st.markdown("### 🏆 累计排名")

    display_df = df[["player_name", "total_points", "game_count",
                      "total_landlord", "total_landlord_win",
                      "total_farmer", "total_farmer_win",
                      "first_game", "last_game"]].copy()
    display_df.columns = ["玩家", "累计分数", "对局数",
                          "地主总次数", "地主赢次",
                          "农民总次数", "农民赢次",
                          "首次参与", "最近参与"]
    display_df["地主胜率"] = display_df.apply(
        lambda r: f"{r['地主赢次']/r['地主总次数']*100:.0f}%" if r["地主总次数"] > 0 else "-", axis=1
    )
    display_df["农民胜率"] = display_df.apply(
        lambda r: f"{r['农民赢次']/r['农民总次数']*100:.0f}%" if r["农民总次数"] > 0 else "-", axis=1
    )
    display_df["累计分数"] = display_df["累计分数"].apply(lambda x: f"{x:+.0f}")
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    fig = px.bar(
        df,
        x="player_name",
        y="total_points",
        color="total_points",
        color_continuous_scale=["red", "gray", "green"],
        color_continuous_midpoint=0,
        title="各玩家累计分数",
        labels={"player_name": "玩家", "total_points": "累计分数"},
    )
    fig.update_layout(xaxis_title="玩家", yaxis_title="累计分数")
    st.plotly_chart(fig, use_container_width=True)

    fig2 = px.pie(
        df,
        values="game_count",
        names="player_name",
        title="各玩家对局数占比",
    )
    st.plotly_chart(fig2, use_container_width=True)

# ---- 按月统计 ----
elif strategy == "按月统计":
    monthly = get_player_stats_by_month()
    df = pd.DataFrame(monthly)

    st.markdown("### 📅 月度统计")

    pivot = df.pivot_table(index="month", columns="player_name", values="total_points", fill_value=0)
    fig = go.Figure()
    for col in pivot.columns:
        fig.add_trace(go.Bar(name=col, x=pivot.index, y=pivot[col]))
    fig.update_layout(barmode="group", title="各玩家月度分数", xaxis_title="月份", yaxis_title="分数")
    st.plotly_chart(fig, use_container_width=True)

    fig2 = px.line(
        df,
        x="month",
        y="total_points",
        color="player_name",
        title="月度分数趋势",
        markers=True,
        labels={"month": "月份", "total_points": "分数", "player_name": "玩家"},
    )
    st.plotly_chart(fig2, use_container_width=True)

    display_df = df.copy()
    display_df.columns = ["玩家", "月份", "分数", "对局数"]
    display_df["分数"] = display_df["分数"].apply(lambda x: f"{x:+.0f}")
    st.dataframe(display_df, use_container_width=True, hide_index=True)

# ---- 按日统计 ----
elif strategy == "按日统计":
    daily = get_player_stats_by_day()
    if not daily:
        st.info("暂无数据")
        st.stop()

    df = pd.DataFrame(daily)

    st.markdown("### 📆 每日统计")

    # 分组柱状图
    pivot = df.pivot_table(index="day", columns="player_name", values="total_points", fill_value=0)
    fig = go.Figure()
    for col in pivot.columns:
        fig.add_trace(go.Bar(name=col, x=pivot.index, y=pivot[col]))
    fig.update_layout(barmode="group", title="各玩家每日分数", xaxis_title="日期", yaxis_title="分数")
    st.plotly_chart(fig, use_container_width=True)

    # 累计趋势折线图
    fig2 = px.line(
        df,
        x="day",
        y="total_points",
        color="player_name",
        title="每日分数趋势",
        markers=True,
        labels={"day": "日期", "total_points": "分数", "player_name": "玩家"},
    )
    st.plotly_chart(fig2, use_container_width=True)

    # 堆叠面积图
    fig3 = go.Figure()
    for col in pivot.columns:
        fig3.add_trace(go.Scatter(
            x=pivot.index,
            y=pivot[col],
            name=col,
            stackgroup="one",
        ))
    fig3.update_layout(title="每日累计分数（堆叠）", xaxis_title="日期", yaxis_title="分数")
    st.plotly_chart(fig3, use_container_width=True)

    # 详细数据表
    display_df = df.copy()
    display_df.columns = ["玩家", "日期", "分数", "对局数"]
    display_df["分数"] = display_df["分数"].apply(lambda x: f"{x:+.0f}")
    st.dataframe(display_df, use_container_width=True, hide_index=True)

# ---- 按局统计 ----
elif strategy == "按局统计":
    session_data = get_player_stats_by_session()
    if not session_data:
        st.info("暂无数据")
        st.stop()

    st.markdown("### 🎮 按局统计")

    df = pd.DataFrame(session_data)
    grouped = df.groupby(["game_session_id", "game_date", "game_time"])

    for (sid, game_date, game_time), group in grouped:
        players_str = " | ".join(
            f"{row['player_name']}{'🟢' if row['win_points'] >= 0 else '🔴'}{row['win_points']:+.0f}分"
            for _, row in group.sort_values("win_points", ascending=False).iterrows()
        )

        with st.expander(f"🎲 {game_date} {game_time}  |  {players_str}"):
            col1, col2 = st.columns(2)

            with col1:
                st.dataframe(
                    group[["player_name", "win_points"]].rename(
                        columns={"player_name": "玩家", "win_points": "分数"}
                    ).sort_values("分数", ascending=False),
                    use_container_width=True,
                    hide_index=True,
                )

            with col2:
                positive = group[group["win_points"] > 0]
                if len(positive) > 0:
                    fig = px.pie(
                        positive,
                        values="win_points",
                        names="player_name",
                        title="赢家分数占比",
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("本局无赢家")
