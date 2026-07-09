from telethon import TelegramClient

from bot.config import config

# Single shared Telethon client. Started with the bot token so it operates as
# the bot account, giving Aiogram-side services access to MTProto-only calls
# (premium emoji entities, pack extraction, inline message editing, channel
# permission checks) that the Bot API cannot perform.
client = TelegramClient(config.session_path, config.api_id, config.api_hash)


async def start_client() -> None:
    await client.start(bot_token=config.bot_token)


async def stop_client() -> None:
    await client.disconnect()
