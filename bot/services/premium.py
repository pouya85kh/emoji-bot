"""
Premium emoji service.

Wraps the MTProto-only helpers in telethon_client/premium.py with the
business logic (DB reads/writes, pagination, limits) that in the original
bot lived directly inside the Telethon event handlers. Handlers call into
this service instead of talking to the database or building entities
themselves.
"""
from dataclasses import dataclass

from bot.config import config
from bot.database import database as db
from bot.database.models import SavedEmoji
from bot.telethon_client import premium as premium_tl


def premiumize(text: str) -> tuple[str, list]:
    return premium_tl.premiumize(text)


def with_deco(key: str, text: str) -> tuple[str, list]:
    return premium_tl.with_deco(key, text)


def utf16_len(text: str) -> int:
    return premium_tl.utf16_len(text)


@dataclass
class MyEmojisPage:
    text: str
    entities: list
    rows: list[SavedEmoji]
    page: int
    total_pages: int


def render_my_emojis_page(lang: str | None, user_id: int, page: int = 0) -> MyEmojisPage:
    from bot.utils.i18n import t

    rows = [SavedEmoji.from_row(r) for r in db.list_saved_emojis(user_id)]
    total = len(rows)
    limit = db.user_limit(user_id)
    limit_txt = t(lang, "unlimited") if limit is None else str(limit)

    total_pages = max(1, (total + config.page_size - 1) // config.page_size)
    page = max(0, min(page, total_pages - 1))
    page_rows = rows[page * config.page_size:(page + 1) * config.page_size]

    text = t(lang, "my_emojis_header", total=total, limit=limit_txt)
    entities = []

    if not page_rows:
        text += t(lang, "my_emojis_empty")
    else:
        for i, r in enumerate(page_rows, start=1):
            alt = r.alt if r.alt else config.fallback_emoji
            text += f"{i}. "
            offset = utf16_len(text)
            from telethon.tl import types
            entities.append(types.MessageEntityCustomEmoji(
                offset=offset, length=utf16_len(alt), document_id=r.doc_id,
            ))
            text += f"{alt}  {r.name}\n"

    return MyEmojisPage(text=text, entities=entities, rows=page_rows, page=page, total_pages=total_pages)


def can_add_emoji(user_id: int) -> bool:
    limit = db.user_limit(user_id)
    return limit is None or db.user_emoji_count(user_id) < limit


def save_emoji(user_id: int, name: str, doc_id: int, alt: str | None) -> None:
    db.add_saved_emoji(user_id, name, doc_id, alt)


def delete_emoji(row_id: int, user_id: int) -> None:
    db.delete_saved_emoji(row_id, user_id)


def default_emoji_name(lang: str | None, doc_id: int) -> str:
    from bot.utils.i18n import t
    return t(lang, "add_emoji_default_name", doc_id=doc_id)


def is_default_name_word(lang: str | None, name: str) -> bool:
    from bot.utils.i18n import t
    default_words = {
        t("fa", "add_emoji_default_word_1"), t("fa", "add_emoji_default_word_2"),
        t("en", "add_emoji_default_word_1"), t("en", "add_emoji_default_word_2"),
    }
    return name in default_words
