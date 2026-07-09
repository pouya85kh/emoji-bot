"""
Entrypoint.

Architecture (see telethon_client/inline.py for the detailed rationale):

- Aiogram's Dispatcher is the single consumer of updates for all business
  logic (messages, callback queries, inline queries, channel posts). It's
  the "brain" of the bot.
- The shared Telethon client (bot.telethon_client.client.client) is used
  purely as an RPC client for MTProto-only operations: sending/editing any
  message that carries premium-emoji entities, sticker/emoji pack fetching,
  and channel permission checks.
- The one exception is UpdateBotInlineSend: Telegram does not deliver this
  as a Bot API update at all, so it must be handled as a raw Telethon event.
  It's registered here, isolated from all other business logic, so there is
  no duplicate update processing between the two clients.

Both are run concurrently with asyncio.gather.
"""
import asyncio

from telethon import events

from bot.database.database import db_init
from bot.handlers import routers
from bot.loader import bot, dp
from bot.middlewares.error import setup_logging
from bot.telethon_client.client import client, start_client, stop_client
from bot.telethon_client.inline import edit_inline_message
from bot.telethon_client.premium import parse_query


async def _on_bot_inline_send(event) -> None:
    if not event.msg_id:
        return

    query = (event.query or "").strip()
    text, entities = parse_query(query)
    if not entities:
        return

    for attempt in range(3):
        try:
            await asyncio.sleep(0.4 * (attempt + 1))
            await edit_inline_message(event.msg_id, text, entities)
            return
        except Exception as e:
            print(f"Edit failed (attempt {attempt + 1}): {e}")


async def main() -> None:
    setup_logging()
    db_init()

    for router in routers:
        dp.include_router(router)

    await start_client()

    from telethon.tl.types import UpdateBotInlineSend
    client.add_event_handler(_on_bot_inline_send, events.Raw(UpdateBotInlineSend))

    await bot.delete_webhook(drop_pending_updates=True)

    print("Bot started...")
    try:
        await asyncio.gather(
            dp.start_polling(bot),
            client.run_until_disconnected(),
        )
    finally:
        await stop_client()


if __name__ == "__main__":
    asyncio.run(main())
