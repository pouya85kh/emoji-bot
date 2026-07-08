from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_PREMIUM_EMOJI_ID = 5057918405923832965


def _parse_admin_ids(raw: str | None) -> set[int]:
    if not raw:
        return {7049497099}
    result: set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            result.add(int(part))
    return result or {7049497099}


def _parse_json_map(raw: str | None) -> dict[str, int]:
    if not raw:
        return {}
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("PREMIUM_EMOJI_MAP must be a JSON object")
    return {str(k): int(v) for k, v in data.items()}


@dataclass(slots=True)
class Settings:
    api_id: int
    api_hash: str
    bot_token: str
    session_path: str = "/data/bot"
    db_path: str = "bot.db"
    admin_ids: set[int] = field(default_factory=set)
    support_username: str = "nooooofear"
    default_emoji_limit: int = 50
    channel_min_members: int = 50
    fallback_emoji: str = "⭐"
    locales_dir: Path = Path(__file__).resolve().parent / "locales"
    premium_emoji_map: dict[str, int] = field(default_factory=dict)

    @classmethod
    def from_env(cls) -> "Settings":
        premium = _parse_json_map(os.environ.get("PREMIUM_EMOJI_MAP"))
        if not premium:
            premium = {k: DEFAULT_PREMIUM_EMOJI_ID for k in [
                "rocket", "telegram", "star", "link", "panel", "help", "mail", "gem",
                "bolt", "note", "mic", "gift", "chart", "folder", "check", "gear",
                "pencil", "dino", "ticket", "back",
            ]}
        return cls(
            api_id=int(os.environ["API_ID"]),
            api_hash=os.environ["API_HASH"],
            bot_token=os.environ["BOT_TOKEN"],
            session_path=os.environ.get("SESSION_PATH", "/data/bot"),
            db_path=os.environ.get("DB_PATH", "bot.db"),
            admin_ids=_parse_admin_ids(os.environ.get("ADMIN_IDS")),
            support_username=os.environ.get("SUPPORT_USERNAME", "nooooofear"),
            default_emoji_limit=int(os.environ.get("DEFAULT_EMOJI_LIMIT", "50")),
            channel_min_members=int(os.environ.get("CHANNEL_MIN_MEMBERS", "50")),
            fallback_emoji=os.environ.get("FALLBACK_EMOJI", "⭐"),
            premium_emoji_map=premium,
        )
