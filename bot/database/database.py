"""
Database layer.

Kept as raw sqlite3 (not SQLAlchemy) deliberately: the original bot used a
handful of simple, well-defined queries against a tiny schema. Introducing an
ORM here would be a rewrite, not a migration, and risks silently changing
query semantics (e.g. NULL handling, autoincrement behaviour). Schema,
column names, and every query below are preserved verbatim from bot.py.
"""
import asyncio
import datetime
import random
import sqlite3
import string

from bot.config import config

_db_lock = asyncio.Lock()
_conn = sqlite3.connect(config.db_path, check_same_thread=False)
_conn.row_factory = sqlite3.Row


def db_init() -> None:
    cur = _conn.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS users(
            user_id INTEGER PRIMARY KEY,
            first_name TEXT,
            username TEXT,
            emoji_limit INTEGER DEFAULT 50,
            unlimited INTEGER DEFAULT 0,
            set_code TEXT,
            joined_at TEXT,
            language TEXT
        );
        CREATE TABLE IF NOT EXISTS saved_emojis(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT,
            doc_id INTEGER,
            alt TEXT
        );
        CREATE TABLE IF NOT EXISTS channels(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            channel_id TEXT,
            title TEXT
        );
        CREATE TABLE IF NOT EXISTS tickets(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            message TEXT,
            status TEXT DEFAULT 'open',
            created_at TEXT
        );
        """
    )
    _conn.commit()

    # Migrations for older DBs (kept from original, plus new `language` column
    # needed for the localization feature added in this migration).
    for stmt in (
        "ALTER TABLE saved_emojis ADD COLUMN alt TEXT",
        "ALTER TABLE users ADD COLUMN language TEXT",
    ):
        try:
            cur.execute(stmt)
            _conn.commit()
        except sqlite3.OperationalError:
            pass


def ensure_user(user_id: int, first_name: str | None = None, username: str | None = None) -> None:
    cur = _conn.cursor()
    cur.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    if row is None:
        cur.execute(
            "INSERT INTO users(user_id, first_name, username, emoji_limit, unlimited, joined_at) "
            "VALUES(?,?,?,?,?,?)",
            (user_id, first_name, username, config.default_emoji_limit, 0,
             datetime.datetime.utcnow().isoformat()),
        )
        _conn.commit()
    else:
        cur.execute("UPDATE users SET first_name=?, username=? WHERE user_id=?",
                     (first_name, username, user_id))
        _conn.commit()


def get_user(user_id: int) -> sqlite3.Row | None:
    cur = _conn.cursor()
    cur.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    return cur.fetchone()


def get_user_language(user_id: int) -> str | None:
    u = get_user(user_id)
    return u["language"] if u and u["language"] else None


def set_user_language(user_id: int, language: str) -> None:
    cur = _conn.cursor()
    cur.execute("UPDATE users SET language=? WHERE user_id=?", (language, user_id))
    _conn.commit()


def user_emoji_count(user_id: int) -> int:
    cur = _conn.cursor()
    cur.execute("SELECT COUNT(*) c FROM saved_emojis WHERE user_id=?", (user_id,))
    return cur.fetchone()["c"]


def user_limit(user_id: int) -> int | None:
    u = get_user(user_id)
    if u is None:
        return config.default_emoji_limit
    if u["unlimited"]:
        return None  # unlimited
    return u["emoji_limit"]


def add_saved_emoji(user_id: int, name: str, doc_id: int, alt: str | None = None) -> None:
    cur = _conn.cursor()
    cur.execute("INSERT INTO saved_emojis(user_id, name, doc_id, alt) VALUES(?,?,?,?)",
                (user_id, name, doc_id, alt))
    _conn.commit()


def list_saved_emojis(user_id: int) -> list[sqlite3.Row]:
    cur = _conn.cursor()
    cur.execute("SELECT * FROM saved_emojis WHERE user_id=? ORDER BY id", (user_id,))
    return cur.fetchall()


def delete_saved_emoji(row_id: int, user_id: int) -> None:
    cur = _conn.cursor()
    cur.execute("DELETE FROM saved_emojis WHERE id=? AND user_id=?", (row_id, user_id))
    _conn.commit()


def get_or_create_set_code(user_id: int) -> str:
    u = get_user(user_id)
    if u and u["set_code"]:
        return u["set_code"]
    code = "".join(random.choices(string.ascii_uppercase + string.digits, k=7))
    cur = _conn.cursor()
    cur.execute("UPDATE users SET set_code=? WHERE user_id=?", (code, user_id))
    _conn.commit()
    return code


def find_user_by_set_code(code: str) -> sqlite3.Row | None:
    cur = _conn.cursor()
    cur.execute("SELECT * FROM users WHERE set_code=?", (code,))
    return cur.fetchone()


def add_channel(user_id: int, channel_id: int | str, title: str | None) -> bool:
    cur = _conn.cursor()
    cur.execute("SELECT id FROM channels WHERE channel_id=?", (str(channel_id),))
    if cur.fetchone():
        return False
    cur.execute("INSERT INTO channels(user_id, channel_id, title) VALUES(?,?,?)",
                (user_id, str(channel_id), title))
    _conn.commit()
    return True


def list_channels(user_id: int) -> list[sqlite3.Row]:
    cur = _conn.cursor()
    cur.execute("SELECT * FROM channels WHERE user_id=?", (user_id,))
    return cur.fetchall()


def is_registered_channel(channel_id: int | str) -> sqlite3.Row | None:
    cur = _conn.cursor()
    cur.execute("SELECT * FROM channels WHERE channel_id=?", (str(channel_id),))
    return cur.fetchone()


def add_ticket(user_id: int, message: str) -> None:
    cur = _conn.cursor()
    cur.execute(
        "INSERT INTO tickets(user_id, message, status, created_at) VALUES(?,?,?,?)",
        (user_id, message, "open", datetime.datetime.utcnow().isoformat()),
    )
    _conn.commit()


def stats() -> dict:
    cur = _conn.cursor()
    cur.execute("SELECT COUNT(*) c FROM users")
    users_count = cur.fetchone()["c"]
    cur.execute("SELECT COUNT(*) c FROM saved_emojis")
    emojis_count = cur.fetchone()["c"]
    cur.execute("SELECT COUNT(*) c FROM channels")
    channels_count = cur.fetchone()["c"]
    cur.execute("SELECT COUNT(*) c FROM tickets WHERE status='open'")
    open_tickets = cur.fetchone()["c"]
    cur.execute("SELECT COUNT(*) c FROM users WHERE unlimited=1")
    unlimited_users = cur.fetchone()["c"]
    return {
        "users": users_count,
        "emojis": emojis_count,
        "channels": channels_count,
        "open_tickets": open_tickets,
        "unlimited_users": unlimited_users,
    }


def all_user_ids() -> list[int]:
    cur = _conn.cursor()
    cur.execute("SELECT user_id FROM users")
    return [r["user_id"] for r in cur.fetchall()]


def set_unlimited(user_id: int) -> None:
    cur = _conn.cursor()
    cur.execute("UPDATE users SET unlimited=1 WHERE user_id=?", (user_id,))
    _conn.commit()
