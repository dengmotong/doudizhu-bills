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
    display_df["首次参与"] = display_df["首次参与"].apply(lambda d: f"{d[:4]}年{int(d[5:7])}月{int(d[8:10])}日")
    display_df["最近参与"] = display_df["最近参与"].apply(lambda d: f"{d[:4]}年{int(d[5:7])}月{int(d[8:10])}日")
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

    df["month_label"] = df["month"].apply(lambda m: f"{m[:4]}年{int(m[5:7])}月")
    df = df.sort_values(["player_name", "month"])
    df["cumulative"] = df.groupby("player_name")["total_points"].cumsum()

    # 月度累计趋势（替代原月度分数趋势）
    fig = px.line(
        df,
        x="month",
        y="cumulative",
        color="player_name",
        title="月度累计分数趋势",
        markers=True,
        labels={"month": "月份", "cumulative": "累计分数", "player_name": "玩家"},
    )
    fig.update_xaxes(
        tickvals=sorted(df["month"].unique()),
        ticktext=[f"{m[:4]}年{int(m[5:7])}月" for m in sorted(df["month"].unique())],
    )
    st.plotly_chart(fig, use_container_width=True)

    # 分组柱状图（不填充缺失月份）
    pivot = df.pivot_table(index="month", columns="player_name", values="total_points")
    pivot = pivot.dropna(how="all")
    fig2 = go.Figure()
    for col in pivot.columns:
        fig2.add_trace(go.Bar(name=col, x=pivot.index, y=pivot[col]))
    fig2.update_layout(barmode="group", title="各玩家月度分数", xaxis_title="月份", yaxis_title="分数")
    fig2.update_xaxes(
        tickvals=pivot.index,
        ticktext=[f"{m[:4]}年{int(m[5:7])}月" for m in pivot.index],
    )
    st.plotly_chart(fig2, use_container_width=True)

    display_df = df[["month_label", "player_name", "total_points", "game_count", "cumulative"]].copy()
    display_df.columns = ["月份", "玩家", "分数", "对局数", "累计分数"]
    display_df["分数"] = display_df["分数"].apply(lambda x: f"{x:+.0f}")
    display_df["累计分数"] = display_df["累计分数"].apply(lambda x: f"{x:+.0f}")
    st.dataframe(display_df, use_container_width=True, hide_index=True)

# ---- 按日统计 ----
elif strategy == "按日统计":
    daily = get_player_stats_by_day()
    if not daily:
        st.info("暂无数据")
        st.stop()

    df = pd.DataFrame(daily)

    st.markdown("### 📆 每日统计")

    # 数值索引 = 日期紧挨排列，无空隙
    all_days = sorted(df["day"].unique())
    day_to_idx = {d: i for i, d in enumerate(all_days)}
    day_labels = {d: f"{d[:4]}年{int(d[5:7])}月{int(d[8:10])}日" for d in all_days}

    df["day_idx"] = df["day"].map(day_to_idx)
    df = df.sort_values(["player_name", "day"])
    df["cumulative"] = df.groupby("player_name")["total_points"].cumsum()

    # 分组柱状图
    pivot = df.pivot_table(index="day", columns="player_name", values="total_points", aggfunc="sum")
    pivot = pivot.reindex(all_days).dropna(how="all")
    x_pos = list(range(len(pivot)))

    fig = go.Figure()
    for col in pivot.columns:
        fig.add_trace(go.Bar(name=col, x=x_pos, y=pivot[col].values))
    fig.update_layout(
        barmode="group",
        title="各玩家每日分数",
        xaxis_title="日期",
        yaxis_title="分数",
        xaxis=dict(
            tickvals=x_pos,
            ticktext=[day_labels[d] for d in pivot.index],
        ),
    )
    st.plotly_chart(fig, use_container_width=True)

    # 累计折线图（无填充阴影）
    fig3 = go.Figure()
    for player in sorted(df["player_name"].unique()):
        player_df = df[df["player_name"] == player].sort_values("day")
        fig3.add_trace(go.Scatter(
            x=player_df["day_idx"],
            y=player_df["cumulative"],
            name=player,
            mode="lines+markers",
        ))
    all_cum = df["cumulative"]
    max_abs = max(abs(all_cum.min()), abs(all_cum.max()), 1)
    fig3.update_layout(
        title="每日累计分数趋势",
        xaxis_title="日期",
        yaxis_title="累计分数",
        xaxis=dict(
            tickvals=list(range(len(all_days))),
            ticktext=[day_labels[d] for d in all_days],
        ),
        yaxis=dict(
            range=[-max_abs * 1.15, max_abs * 1.15],
            zeroline=True,
            zerolinewidth=2,
            zerolinecolor="black",
        ),
    )
    st.plotly_chart(fig3, use_container_width=True)

    # 详细数据表
    display_df = df.copy()
    display_df["day_label"] = display_df["day"].map(day_labels)
    display_df = display_df[["day_label", "player_name", "total_points", "game_count", "cumulative"]]
    display_df.columns = ["日期", "玩家", "分数", "对局数", "累计分数"]
    display_df["分数"] = display_df["分数"].apply(lambda x: f"{x:+.0f}")
    display_df["累计分数"] = display_df["累计分数"].apply(lambda x: f"{x:+.0f}")
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

        date_label = f"{game_date[:4]}年{int(game_date[5:7])}月{int(game_date[8:10])}日" if game_date else ""
        with st.expander(f"🎲 {date_label} {game_time}  |  {players_str}"):
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
