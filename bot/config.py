import os
import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Config:
    api_id: int = int(os.environ["API_ID"])
    api_hash: str = os.environ["API_HASH"]
    bot_token: str = os.environ["BOT_TOKEN"]

    admin_ids: frozenset = field(default_factory=lambda: frozenset({7049497099}))
    support_username: str = "nooooofear"

    fallback_emoji: str = "\u2b50"

    default_emoji_limit: int = 50
    channel_min_members: int = 50

    db_path: str = os.environ.get("DB_PATH", "bot.db")
    session_path: str = os.environ.get("SESSION_PATH", "/data/bot")

    # placeholder decorative-emoji document id (must be replaced with a real
    # premium emoji document id the bot account has access to, exactly as in
    # the original bot -- otherwise messages using it will fail to send)
    deco_emoji_id: int = 5057918405923832965

    page_size: int = 5


config = Config()

PACK_LINK_RE = re.compile(r"(?:addemoji|addstickers)/([a-zA-Z0-9_]+)")
CODE_RE = re.compile(r"\[(\d+)\]")

# Every decorative-slot key used across the original bot, all mapped to the
# same placeholder id (see original EMOJI dict) -- replace deco_emoji_id above
# once you have a real premium-emoji document id.
EMOJI_KEYS = [
    "rocket", "telegram", "star", "link", "panel", "help", "mail", "gem",
    "bolt", "note", "mic", "gift", "chart", "folder", "check", "gear",
    "pencil", "dino", "ticket", "back",
]

EMOJI = {key: config.deco_emoji_id for key in EMOJI_KEYS}

# Unicode-glyph -> decorative key map used by premiumize()
UNICODE_EMOJI_MAP = {
    "🚀": "rocket", "✈️": "telegram", "⭐": "star", "🔗": "link", "🖥": "panel",
    "❓": "help", "✉️": "mail", "💎": "gem", "⚡": "bolt", "📝": "note",
    "🎙": "mic", "🎁": "gift", "📊": "chart", "📋": "folder", "✅": "check",
    "⌘": "gear", "✏️": "pencil", "🦖": "dino", "🖼": "ticket", "🔙": "back",
    "📈": "rocket", "📨": "mail", "🔷": "bolt", "🎉": "gift", "📤": "link",
    "🅰": "note", "🔓": "check", "📢": "mail", "⏳": "bolt",
}
