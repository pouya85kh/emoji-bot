"""
Set-sharing service: generating a shareable code for a user's saved emojis
and applying another user's shared set to the current user (respecting their
emoji limit), exactly as the original /start deep-link handler did.
"""
from bot.database import database as db
from bot.database.models import User
from bot.telethon_client import inline as tl_inline


def get_or_create_set_code(user_id: int) -> str:
    return db.get_or_create_set_code(user_id)


async def build_set_link(code: str) -> str:
    username = await tl_inline.get_bot_username()
    return f"https://t.me/{username}?start=set_{code}"


def apply_shared_set(target_user_id: int, code: str) -> int | None:
    """Copy the owner's saved emojis (referenced by `code`) into
    target_user_id's saved emojis, honoring the target's limit. Returns the
    number of emojis added, or None if the code is invalid."""
    owner_row = db.find_user_by_set_code(code)
    if not owner_row:
        return None
    owner = User.from_row(owner_row)

    src_emojis = db.list_saved_emojis(owner.user_id)
    limit = db.user_limit(target_user_id)
    added = 0
    for row in src_emojis:
        if limit is not None and db.user_emoji_count(target_user_id) >= limit:
            break
        db.add_saved_emoji(target_user_id, row["name"], row["doc_id"])
        added += 1
    return added
