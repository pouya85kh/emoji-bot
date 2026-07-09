import asyncio

from bot.config import config
from bot.database import database as db
from bot.telethon_client import inline as tl_inline


def is_admin(user_id: int) -> bool:
    return user_id in config.admin_ids


def get_stats() -> dict:
    return db.stats()


def unlimit_user(user_id: int) -> None:
    db.ensure_user(user_id)
    db.set_unlimited(user_id)


async def broadcast(text: str, message_template: str) -> tuple[int, int]:
    """Send `message_template.format(text=text)` to every known user.
    Returns (sent_count, failed_count)."""
    ids = db.all_user_ids()
    sent, failed = 0, 0
    for uid in ids:
        ok = await tl_inline.safe_send(uid, message_template.format(text=text))
        if ok:
            sent += 1
        else:
            failed += 1
        await asyncio.sleep(0.05)
    return sent, failed
