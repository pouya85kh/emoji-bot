from __future__ import annotations

import asyncio
import datetime as dt
import random
import sqlite3
import string
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from bot.config import Settings


@dataclass(slots=True)
class UserRecord:
    user_id: int
    first_name: str | None
    username: str | None
    emoji_limit: int
    unlimited: int
    set_code: str | None
    joined_at: str | None
    lang: str | None


@dataclass(slots=True)
class EmojiRecord:
    id: int
    user_id: int
    name: str
    doc_id: int
    alt: str | None


@dataclass(slots=True)
class ChannelRecord:
    id: int
    user_id: int
    channel_id: str
    title: str | None


class Database:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.path = Path(settings.db_path)
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = asyncio.Lock()

    async def init(self) -> None:
        async with self._lock:
            await asyncio.to_thread(self._init_sync)

    def _init_sync(self) -> None:
        cur = self._conn.cursor()
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
                lang TEXT
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
        cur.execute("PRAGMA table_info(users)")
        user_cols = {r[1] for r in cur.fetchall()}
        cur.execute("PRAGMA table_info(saved_emojis)")
        emoji_cols = {r[1] for r in cur.fetchall()}
        if "lang" not in user_cols:
            cur.execute("ALTER TABLE users ADD COLUMN lang TEXT")
        if "joined_at" not in user_cols:
            cur.execute("ALTER TABLE users ADD COLUMN joined_at TEXT")
        if "set_code" not in user_cols:
            cur.execute("ALTER TABLE users ADD COLUMN set_code TEXT")
        if "unlimited" not in user_cols:
            cur.execute("ALTER TABLE users ADD COLUMN unlimited INTEGER DEFAULT 0")
        if "emoji_limit" not in user_cols:
            cur.execute(f"ALTER TABLE users ADD COLUMN emoji_limit INTEGER DEFAULT {self.settings.default_emoji_limit}")
        if "alt" not in emoji_cols:
            cur.execute("ALTER TABLE saved_emojis ADD COLUMN alt TEXT")
        self._conn.commit()

    async def _run(self, func, *args, **kwargs):
        async with self._lock:
            return await asyncio.to_thread(func, *args, **kwargs)

    def _fetchone(self, sql: str, params: tuple[Any, ...] = ()) -> sqlite3.Row | None:
        cur = self._conn.cursor()
        cur.execute(sql, params)
        return cur.fetchone()

    def _fetchall(self, sql: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
        cur = self._conn.cursor()
        cur.execute(sql, params)
        return cur.fetchall()

    def _execute(self, sql: str, params: tuple[Any, ...] = ()) -> None:
        cur = self._conn.cursor()
        cur.execute(sql, params)
        self._conn.commit()

    async def ensure_user(self, user_id: int, first_name: str | None = None, username: str | None = None) -> None:
        def _sync():
            cur = self._conn.cursor()
            cur.execute("SELECT 1 FROM users WHERE user_id=?", (user_id,))
            if cur.fetchone() is None:
                cur.execute(
                    "INSERT INTO users(user_id, first_name, username, emoji_limit, unlimited, set_code, joined_at, lang) VALUES(?,?,?,?,?,?,?,?)",
                    (user_id, first_name, username, self.settings.default_emoji_limit, 0, None, dt.datetime.utcnow().isoformat(), None),
                )
            else:
                cur.execute("UPDATE users SET first_name=?, username=? WHERE user_id=?", (first_name, username, user_id))
            self._conn.commit()
        await self._run(_sync)

    async def get_user(self, user_id: int) -> UserRecord | None:
        row = await self._run(self._fetchone, "SELECT * FROM users WHERE user_id=?", (user_id,))
        return UserRecord(**dict(row)) if row else None

    async def get_locale(self, user_id: int) -> str | None:
        row = await self._run(self._fetchone, "SELECT lang FROM users WHERE user_id=?", (user_id,))
        return row["lang"] if row else None

    async def set_locale(self, user_id: int, lang: str) -> None:
        await self._run(self._execute, "UPDATE users SET lang=? WHERE user_id=?", (lang, user_id))

    async def user_emoji_count(self, user_id: int) -> int:
        row = await self._run(self._fetchone, "SELECT COUNT(*) c FROM saved_emojis WHERE user_id=?", (user_id,))
        return int(row["c"] if row else 0)

    async def user_limit(self, user_id: int) -> int | None:
        row = await self._run(self._fetchone, "SELECT emoji_limit, unlimited FROM users WHERE user_id=?", (user_id,))
        if row is None:
            return self.settings.default_emoji_limit
        if int(row["unlimited"] or 0):
            return None
        return int(row["emoji_limit"] or self.settings.default_emoji_limit)

    async def add_saved_emoji(self, user_id: int, name: str, doc_id: int, alt: str | None = None) -> None:
        await self._run(self._execute, "INSERT INTO saved_emojis(user_id, name, doc_id, alt) VALUES(?,?,?,?)", (user_id, name, int(doc_id), alt))

    async def list_saved_emojis(self, user_id: int) -> list[EmojiRecord]:
        rows = await self._run(self._fetchall, "SELECT * FROM saved_emojis WHERE user_id=? ORDER BY id", (user_id,))
        return [EmojiRecord(**dict(r)) for r in rows]

    async def delete_saved_emoji(self, row_id: int, user_id: int) -> None:
        await self._run(self._execute, "DELETE FROM saved_emojis WHERE id=? AND user_id=?", (row_id, user_id))

    async def get_or_create_set_code(self, user_id: int) -> str:
        user = await self.get_user(user_id)
        if user and user.set_code:
            return user.set_code
        code = "".join(random.choices(string.ascii_uppercase + string.digits, k=7))
        await self._run(self._execute, "UPDATE users SET set_code=? WHERE user_id=?", (code, user_id))
        return code

    async def find_user_by_set_code(self, code: str) -> UserRecord | None:
        row = await self._run(self._fetchone, "SELECT * FROM users WHERE set_code=?", (code,))
        return UserRecord(**dict(row)) if row else None

    async def add_channel(self, user_id: int, channel_id: int | str, title: str | None) -> bool:
        def _sync():
            cur = self._conn.cursor()
            cur.execute("SELECT 1 FROM channels WHERE channel_id=?", (str(channel_id),))
            if cur.fetchone():
                return False
            cur.execute("INSERT INTO channels(user_id, channel_id, title) VALUES(?,?,?)", (user_id, str(channel_id), title))
            self._conn.commit()
            return True
        return await self._run(_sync)

    async def list_channels(self, user_id: int) -> list[ChannelRecord]:
        rows = await self._run(self._fetchall, "SELECT * FROM channels WHERE user_id=? ORDER BY id", (user_id,))
        return [ChannelRecord(**dict(r)) for r in rows]

    async def is_registered_channel(self, channel_id: int | str) -> bool:
        row = await self._run(self._fetchone, "SELECT 1 FROM channels WHERE channel_id=?", (str(channel_id),))
        return row is not None

    async def add_ticket(self, user_id: int, message: str) -> None:
        await self._run(self._execute, "INSERT INTO tickets(user_id, message, status, created_at) VALUES(?,?,?,?)", (user_id, message, "open", dt.datetime.utcnow().isoformat()))

    async def stats(self) -> dict[str, int]:
        users = await self._run(self._fetchone, "SELECT COUNT(*) c FROM users")
        emojis = await self._run(self._fetchone, "SELECT COUNT(*) c FROM saved_emojis")
        channels = await self._run(self._fetchone, "SELECT COUNT(*) c FROM channels")
        tickets = await self._run(self._fetchone, "SELECT COUNT(*) c FROM tickets WHERE status='open'")
        unlimited = await self._run(self._fetchone, "SELECT COUNT(*) c FROM users WHERE unlimited=1")
        return {
            "users": int(users["c"] if users else 0),
            "emojis": int(emojis["c"] if emojis else 0),
            "channels": int(channels["c"] if channels else 0),
            "open_tickets": int(tickets["c"] if tickets else 0),
            "unlimited_users": int(unlimited["c"] if unlimited else 0),
        }

    async def all_user_ids(self) -> list[int]:
        rows = await self._run(self._fetchall, "SELECT user_id FROM users ORDER BY user_id")
        return [int(r["user_id"]) for r in rows]

    async def set_unlimited(self, user_id: int, value: bool = True) -> None:
        await self._run(self._execute, "UPDATE users SET unlimited=? WHERE user_id=?", (1 if value else 0, user_id))
