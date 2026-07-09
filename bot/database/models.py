"""
Lightweight typed views over sqlite3.Row objects returned by database.py.

These are NOT an ORM layer (see database.py docstring for why) -- they just
give handlers/services proper type hints instead of passing raw Row objects
around everywhere.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass


@dataclass(frozen=True)
class User:
    user_id: int
    first_name: str | None
    username: str | None
    emoji_limit: int
    unlimited: bool
    set_code: str | None
    joined_at: str | None
    language: str | None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "User":
        return cls(
            user_id=row["user_id"],
            first_name=row["first_name"],
            username=row["username"],
            emoji_limit=row["emoji_limit"],
            unlimited=bool(row["unlimited"]),
            set_code=row["set_code"],
            joined_at=row["joined_at"],
            language=row["language"] if "language" in row.keys() else None,
        )


@dataclass(frozen=True)
class SavedEmoji:
    id: int
    user_id: int
    name: str
    doc_id: int
    alt: str | None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "SavedEmoji":
        return cls(
            id=row["id"],
            user_id=row["user_id"],
            name=row["name"],
            doc_id=row["doc_id"],
            alt=row["alt"],
        )


@dataclass(frozen=True)
class Channel:
    id: int
    user_id: int
    channel_id: str
    title: str | None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Channel":
        return cls(
            id=row["id"],
            user_id=row["user_id"],
            channel_id=row["channel_id"],
            title=row["title"],
        )
