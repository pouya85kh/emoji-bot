from __future__ import annotations

import asyncio
import logging

from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand
from telethon import TelegramClient

from bot.config import Settings
from bot.database import Database
from bot.handlers import router
from bot.localization import Localizer
from bot.middleware import AppContextMiddleware, LocaleGuardMiddleware
from bot.services import AdminService, AppContext, ChannelsService, EmojiService, InlineService, SupportService, TelethonBridge, UsersService
from bot.telethon_bridge import register_telethon_inline_handler


def build_app() -> AppContext:
    settings = Settings.from_env()
    from aiogram import Bot
    bot = Bot(token=settings.bot_token)
    db = Database(settings)
    localizer = Localizer(settings.locales_dir)
    telethon_client = TelegramClient(settings.session_path, settings.api_id, settings.api_hash)
    bridge = TelethonBridge(telethon_client)

    users = UsersService(db)
    emojis = EmojiService(db, settings)
    channels = ChannelsService(db, settings)
    support = SupportService(db)
    admin = AdminService(db)
    inline = InlineService(emojis)

    return AppContext(
        settings=settings,
        bot=bot,
        db=db,
        localizer=localizer,
        telethon=telethon_client,
        bridge=bridge,
        users=users,
        emojis=emojis,
        channels=channels,
        support=support,
        admin=admin,
        inline=inline,
    )


async def run() -> None:
    logging.basicConfig(level=logging.INFO)
    app = build_app()

    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    for observer in (dp.message, dp.callback_query, dp.inline_query, dp.channel_post):
        observer.middleware(AppContextMiddleware(app))
        observer.middleware(LocaleGuardMiddleware())

    await app.db.init()
    await app.bridge.start(app.settings.bot_token)
    register_telethon_inline_handler(app.telethon, app.bridge)

    await app.bot.set_my_commands([
        BotCommand(command="start", description="Start"),
        BotCommand(command="reply", description="Reply to support"),
    ])

    try:
        await dp.start_polling(app.bot)
    finally:
        await app.bridge.stop()


if __name__ == "__main__":
    asyncio.run(run())
