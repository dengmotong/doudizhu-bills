import sqlite3
from datetime import datetime
from pathlib import Path

from config import DB_PATH


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        );

        CREATE TABLE IF NOT EXISTS game_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_date TEXT NOT NULL,
            game_time TEXT DEFAULT '',
            image_path TEXT,
            raw_text TEXT DEFAULT '',
            price_per_point REAL DEFAULT 5.0,
            settled INTEGER DEFAULT 0,
            settled_at TEXT DEFAULT '',
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        );

        CREATE TABLE IF NOT EXISTS bills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_session_id INTEGER,
            game_date TEXT NOT NULL,
            player_id INTEGER NOT NULL,
            win_points REAL NOT NULL DEFAULT 0,
            landlord_count INTEGER DEFAULT 0,
            landlord_win INTEGER DEFAULT 0,
            farmer_count INTEGER DEFAULT 0,
            farmer_win INTEGER DEFAULT 0,
            remark TEXT DEFAULT '',
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (player_id) REFERENCES players(id),
            FOREIGN KEY (game_session_id) REFERENCES game_sessions(id)
        );
    """)
    _migrate(conn)
    conn.commit()
    conn.close()


def _migrate(conn: sqlite3.Connection):
    migrations = [
        # 旧字段兼容
        "ALTER TABLE game_sessions ADD COLUMN game_time TEXT DEFAULT ''",
        "ALTER TABLE game_sessions ADD COLUMN settled INTEGER DEFAULT 0",
        "ALTER TABLE game_sessions ADD COLUMN settled_at TEXT DEFAULT ''",
        "ALTER TABLE game_sessions ADD COLUMN price_per_point REAL DEFAULT 5.0",
        # 旧 bills 的 win_amount → win_points（重命名思路）
        "ALTER TABLE bills ADD COLUMN win_points REAL NOT NULL DEFAULT 0",
        "ALTER TABLE bills ADD COLUMN game_session_id INTEGER",
        "ALTER TABLE bills ADD COLUMN landlord_count INTEGER DEFAULT 0",
        "ALTER TABLE bills ADD COLUMN landlord_win INTEGER DEFAULT 0",
        "ALTER TABLE bills ADD COLUMN farmer_count INTEGER DEFAULT 0",
        "ALTER TABLE bills ADD COLUMN farmer_win INTEGER DEFAULT 0",
    ]
    for sql in migrations:
        try:
            conn.execute(sql)
        except sqlite3.OperationalError:
            pass

    # 迁移：旧数据 win_amount → win_points
    try:
        conn.execute("""
            UPDATE bills SET win_points = (
                SELECT win_amount FROM bills AS b2 WHERE b2.id = bills.id
            ) WHERE win_points = 0 AND id IN (SELECT id FROM bills WHERE win_amount != 0)
        """)
    except sqlite3.OperationalError:
        pass  # win_amount 列不存在（全新数据库）


# ---- Player CRUD ----

def get_all_players() -> list[dict]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM players ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_player(name: str) -> int:
    conn = get_connection()
    cur = conn.execute("INSERT INTO players (name) VALUES (?)", (name,))
    conn.commit()
    pid = cur.lastrowid
    conn.close()
    return pid


def delete_player(player_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM bills WHERE player_id = ?", (player_id,))
    conn.execute("DELETE FROM players WHERE id = ?", (player_id,))
    conn.commit()
    conn.close()


def rename_player(player_id: int, new_name: str):
    conn = get_connection()
    conn.execute("UPDATE players SET name = ? WHERE id = ?", (new_name, player_id))
    conn.commit()
    conn.close()


# ---- Game Session CRUD ----

def add_game_session(game_date: str, game_time: str, image_path: str, raw_text: str) -> int:
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO game_sessions (game_date, game_time, image_path, raw_text) VALUES (?, ?, ?, ?)",
        (game_date, game_time, image_path, raw_text),
    )
    conn.commit()
    sid = cur.lastrowid
    conn.close()
    return sid


def get_all_game_sessions() -> list[dict]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM game_sessions ORDER BY game_date DESC, id DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_game_session(session_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM bills WHERE game_session_id = ?", (session_id,))
    conn.execute("DELETE FROM game_sessions WHERE id = ?", (session_id,))
    conn.commit()
    conn.close()


def settle_game_session(session_id: int, price_per_point: float):
    conn = get_connection()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        "UPDATE game_sessions SET settled = 1, settled_at = ?, price_per_point = ? WHERE id = ?",
        (now, price_per_point, session_id),
    )
    conn.commit()
    conn.close()


def unsettle_game_session(session_id: int):
    conn = get_connection()
    conn.execute(
        "UPDATE game_sessions SET settled = 0, settled_at = '' WHERE id = ?",
        (session_id,),
    )
    conn.commit()
    conn.close()


def get_session_bills(session_id: int) -> list[dict]:
    conn = get_connection()
    rows = conn.execute("""
        SELECT b.id, b.game_session_id, b.game_date, p.name AS player_name,
               b.win_points, b.landlord_count, b.landlord_win,
               b.farmer_count, b.farmer_win, b.remark, b.created_at
        FROM bills b
        JOIN players p ON b.player_id = p.id
        WHERE b.game_session_id = ?
        ORDER BY b.win_points DESC
    """, (session_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---- Bill CRUD ----

def add_bills(bills: list[dict]):
    """bills: [{"game_session_id": int, "game_date": str, "player_id": int,
               "win_points": float, "landlord_count": int, ...}]"""
    conn = get_connection()
    conn.executemany(
        """INSERT INTO bills
           (game_session_id, game_date, player_id, win_points,
            landlord_count, landlord_win, farmer_count, farmer_win, remark)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            (
                b.get("game_session_id"),
                b["game_date"],
                b["player_id"],
                b["win_points"],
                b.get("landlord_count", 0),
                b.get("landlord_win", 0),
                b.get("farmer_count", 0),
                b.get("farmer_win", 0),
                b.get("remark", ""),
            )
            for b in bills
        ],
    )
    conn.commit()
    conn.close()


def get_all_bills() -> list[dict]:
    conn = get_connection()
    rows = conn.execute("""
        SELECT b.id, b.game_session_id, b.game_date, p.name AS player_name,
               b.win_points, b.landlord_count, b.landlord_win,
               b.farmer_count, b.farmer_win, b.remark, b.created_at
        FROM bills b
        JOIN players p ON b.player_id = p.id
        ORDER BY b.game_date DESC, b.id DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_bills_grouped_by_session() -> list[dict]:
    """按 game_session 分组返回每局数据（跳过无账单的会话）"""
    conn = get_connection()
    sessions = conn.execute("""
        SELECT gs.* FROM game_sessions gs
        WHERE EXISTS (SELECT 1 FROM bills b WHERE b.game_session_id = gs.id)
        ORDER BY gs.game_date DESC, gs.id DESC
    """).fetchall()
    result = []
    for s in sessions:
        bills = conn.execute("""
            SELECT b.id, b.game_session_id, b.game_date, p.name AS player_name,
                   b.win_points, b.landlord_count, b.landlord_win,
                   b.farmer_count, b.farmer_win, b.remark, b.created_at
            FROM bills b
            JOIN players p ON b.player_id = p.id
            WHERE b.game_session_id = ?
            ORDER BY b.win_points DESC
        """, (s["id"],)).fetchall()
        result.append({
            "session": dict(s),
            "bills": [dict(b) for b in bills],
        })
    # 零散账单
    orphan = conn.execute("""
        SELECT b.id, b.game_session_id, b.game_date, p.name AS player_name,
               b.win_points, b.landlord_count, b.landlord_win,
               b.farmer_count, b.farmer_win, b.remark, b.created_at
        FROM bills b
        JOIN players p ON b.player_id = p.id
        WHERE b.game_session_id IS NULL
        ORDER BY b.game_date DESC, b.id DESC
    """).fetchall()
    conn.close()
    if orphan:
        result.append({
            "session": {"id": None, "game_date": "未分组", "game_time": "", "image_path": "", "price_per_point": 5.0, "settled": 0},
            "bills": [dict(b) for b in orphan],
        })
    return result


def update_bill(bill_id: int, game_date: str, player_id: int, win_points: float,
                landlord_count: int, landlord_win: int,
                farmer_count: int, farmer_win: int, remark: str):
    conn = get_connection()
    conn.execute(
        """UPDATE bills SET game_date=?, player_id=?, win_points=?,
           landlord_count=?, landlord_win=?, farmer_count=?, farmer_win=?, remark=?
           WHERE id=?""",
        (game_date, player_id, win_points,
         landlord_count, landlord_win, farmer_count, farmer_win, remark, bill_id),
    )
    conn.commit()
    conn.close()


def delete_bill(bill_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM bills WHERE id = ?", (bill_id,))
    conn.commit()
    conn.close()


# ---- Stats ----

def get_player_cumulative_stats() -> list[dict]:
    conn = get_connection()
    rows = conn.execute("""
        SELECT p.name AS player_name,
               SUM(b.win_points) AS total_points,
               SUM(b.landlord_count) AS total_landlord,
               SUM(b.landlord_win) AS total_landlord_win,
               SUM(b.farmer_count) AS total_farmer,
               SUM(b.farmer_win) AS total_farmer_win,
               COUNT(DISTINCT b.game_session_id) AS game_count,
               MIN(b.game_date) AS first_game,
               MAX(b.game_date) AS last_game
        FROM bills b
        JOIN players p ON b.player_id = p.id
        GROUP BY p.name
        ORDER BY total_points DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_player_stats_by_month() -> list[dict]:
    conn = get_connection()
    rows = conn.execute("""
        SELECT p.name AS player_name,
               strftime('%Y-%m', b.game_date) AS month,
               SUM(b.win_points) AS total_points,
               COUNT(DISTINCT b.game_session_id) AS game_count
        FROM bills b
        JOIN players p ON b.player_id = p.id
        GROUP BY p.name, month
        ORDER BY month
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_player_stats_by_day() -> list[dict]:
    conn = get_connection()
    rows = conn.execute("""
        SELECT p.name AS player_name,
               b.game_date AS day,
               SUM(b.win_points) AS total_points,
               COUNT(DISTINCT b.game_session_id) AS game_count
        FROM bills b
        JOIN players p ON b.player_id = p.id
        GROUP BY p.name, day
        ORDER BY day
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_player_stats_by_session() -> list[dict]:
    """按每局统计每个玩家的得分"""
    conn = get_connection()
    rows = conn.execute("""
        SELECT b.game_session_id, gs.game_date, gs.game_time,
               p.name AS player_name, b.win_points
        FROM bills b
        JOIN players p ON b.player_id = p.id
        JOIN game_sessions gs ON b.game_session_id = gs.id
        ORDER BY gs.game_date DESC, gs.id DESC, b.win_points DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_settled_sessions_with_money() -> list[dict]:
    """获取已结账的会话及对应的金额统计"""
    conn = get_connection()
    rows = conn.execute("""
        SELECT gs.id, gs.game_date, gs.game_time, gs.price_per_point, gs.settled_at,
               p.name AS player_name, b.win_points,
               ROUND(b.win_points * gs.price_per_point, 2) AS win_money
        FROM game_sessions gs
        JOIN bills b ON b.game_session_id = gs.id
        JOIN players p ON b.player_id = p.id
        WHERE gs.settled = 1
        ORDER BY gs.game_date DESC, gs.id DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# 初始化数据库
init_db()
