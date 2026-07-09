from bot.config import config
from bot.database import database as db
from bot.telethon_client import inline as tl_inline


def add_ticket(user_id: int, message: str) -> None:
    db.add_ticket(user_id, message)


async def notify_admins(text: str) -> None:
    for admin_id in config.admin_ids:
        await tl_inline.safe_send(admin_id, text)


async def send_admin_reply(target_id: int, text: str) -> bool:
    return await tl_inline.safe_send(target_id, text)
