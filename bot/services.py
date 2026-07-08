from __future__ import annotations

import asyncio
from dataclasses import dataclass

from aiogram import Bot
from aiogram.types import InlineQueryResultArticle, InputTextMessageContent, Message, MessageEntity
from telethon import TelegramClient
from telethon.tl import functions, types
from telethon.tl.functions.messages import EditInlineBotMessageRequest

from bot.config import Settings
from bot.database import Database
from bot.localization import Localizer
from bot.utils import build_pack_chunk, extract_custom_emoji_pairs, parse_codes, parse_inline_query, premiumize, utf16_len


@dataclass(slots=True)
class AppContext:
    settings: Settings
    bot: Bot
    db: Database
    localizer: Localizer
    telethon: TelegramClient
    bridge: "TelethonBridge"
    users: "UsersService"
    emojis: "EmojiService"
    channels: "ChannelsService"
    support: "SupportService"
    admin: "AdminService"
    inline: "InlineService"


class UsersService:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def ensure(self, user_id: int, first_name: str | None = None, username: str | None = None) -> None:
        await self.db.ensure_user(user_id, first_name, username)

    async def locale(self, user_id: int) -> str | None:
        return await self.db.get_locale(user_id)

    async def set_locale(self, user_id: int, locale: str) -> None:
        await self.db.set_locale(user_id, locale)


class EmojiService:
    def __init__(self, db: Database, settings: Settings) -> None:
        self.db = db
        self.settings = settings

    def premiumize(self, text: str):
        return premiumize(text, self.settings.premium_emoji_map)

    async def count(self, user_id: int) -> int:
        return await self.db.user_emoji_count(user_id)

    async def limit(self, user_id: int) -> int | None:
        return await self.db.user_limit(user_id)

    async def add(self, user_id: int, name: str, doc_id: int, alt: str | None = None) -> None:
        await self.db.add_saved_emoji(user_id, name, doc_id, alt)

    async def delete(self, row_id: int, user_id: int) -> None:
        await self.db.delete_saved_emoji(row_id, user_id)

    async def get_or_create_set_code(self, user_id: int) -> str:
        return await self.db.get_or_create_set_code(user_id)

    async def owner_by_set_code(self, code: str):
        return await self.db.find_user_by_set_code(code)

    async def add_from_owner(self, user_id: int, owner_id: int) -> int:
        src = await self.db.list_saved_emojis(owner_id)
        limit = await self.db.user_limit(user_id)
        count = await self.db.user_emoji_count(user_id)
        added = 0
        for row in src:
            if limit is not None and count >= limit:
                break
            await self.db.add_saved_emoji(user_id, row.name, row.doc_id, row.alt)
            count += 1
            added += 1
        return added

    async def render_page(self, user_id: int, page: int = 0):
        rows = await self.db.list_saved_emojis(user_id)
        total = len(rows)
        limit = await self.db.user_limit(user_id)
        limit_txt = "نامحدود" if limit is None else str(limit)
        page_size = 5
        total_pages = max(1, (total + page_size - 1) // page_size)
        page = max(0, min(page, total_pages - 1))
        page_rows = rows[page * page_size:(page + 1) * page_size]
        text = f"⭐  ایموجی‌های ذخیره‌شده: {total}/{limit_txt}\n" + "─" * 18 + "\n\n"
        entities: list[MessageEntity] = []
        if not page_rows:
            text += "هنوز ایموجی‌ای ذخیره نکردی."
        else:
            for i, row in enumerate(page_rows, start=1):
                alt = row.alt or self.settings.fallback_emoji
                text += f"{i}. "
                offset = utf16_len(text)
                entities.append(MessageEntity(type="custom_emoji", offset=offset, length=utf16_len(alt), custom_emoji_id=str(row.doc_id)))
                text += f"{alt}  {row.name}\n"
        return text, entities, page_rows, total_pages, page

    async def extract_pairs(self, message: Message):
        return extract_custom_emoji_pairs(message)

    async def parse_codes(self, text: str | None):
        return parse_codes(text)

    async def parse_inline(self, query: str):
        return parse_inline_query(query)

    async def build_pack_chunk(self, docs, start_index: int):
        return build_pack_chunk(docs, start_index, fallback=self.settings.fallback_emoji)


class ChannelsService:
    def __init__(self, db: Database, settings: Settings) -> None:
        self.db = db
        self.settings = settings

    async def list(self, user_id: int):
        return await self.db.list_channels(user_id)

    async def is_registered(self, channel_id: int | str) -> bool:
        return await self.db.is_registered_channel(channel_id)

    async def add(self, user_id: int, channel_id: int | str, title: str | None) -> bool:
        return await self.db.add_channel(user_id, channel_id, title)

    async def validate(self, bot: Bot, channel_ref: str) -> tuple[bool, str | None, int | None]:
        try:
            chat = await bot.get_chat(channel_ref)
        except Exception as e:
            return False, f"کانال پیدا نشد: {e}", None
        if chat.type != "channel":
            return False, "این یک کانال معتبر نیست.", None
        try:
            members = await bot.get_chat_member_count(chat.id)
        except Exception:
            members = 0
        if members and members < self.settings.channel_min_members:
            return False, f"کانال باید حداقل {self.settings.channel_min_members} عضو داشته باشد (فعلی: {members}).", None
        try:
            me = await bot.get_chat_member(chat.id, "me")
            if not getattr(me, "is_admin", False) or not getattr(me, "can_edit_messages", False):
                return False, "ربات باید در این کانال ادمین باشد و دسترسی «ویرایش پیام‌ها» داشته باشد.", None
        except Exception as e:
            return False, f"نمی‌توانم دسترسی‌های ربات در کانال را بررسی کنم: {e}", None
        return True, chat.title, chat.id

    async def auto_convert(self, bot: Bot, channel_id: int, message_id: int, text: str) -> bool:
        new_text, entities = parse_inline_query(text)
        if not entities:
            return False
        try:
            await bot.edit_message_text(chat_id=channel_id, message_id=message_id, text=new_text, entities=entities, parse_mode=None)
            return True
        except Exception:
            return False


class SupportService:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def add_ticket(self, user_id: int, message: str) -> None:
        await self.db.add_ticket(user_id, message)


class AdminService:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def stats(self) -> dict[str, int]:
        return await self.db.stats()

    async def unlimit(self, user_id: int) -> None:
        await self.db.ensure_user(user_id)
        await self.db.set_unlimited(user_id, True)

    async def broadcast_targets(self) -> list[int]:
        return await self.db.all_user_ids()


class InlineService:
    def __init__(self, emojis: EmojiService) -> None:
        self.emojis = emojis

    async def build_results(self, query: str):
        text, entities = await self.emojis.parse_inline(query)
        if not query.strip():
            return [
                InlineQueryResultArticle(
                    id="empty",
                    title="✨ ارسال ایموجی پرمیوم",
                    description="پیام خود را بنویسید...",
                    input_message_content=InputTextMessageContent(message_text="مثال: hi [5350291836378307462]"),
                )
            ]
        if not entities:
            return [
                InlineQueryResultArticle(
                    id="bad_format",
                    title="⚠️ فرمت اشتباه",
                    description="مثال: hi [5350291836378307462]",
                    input_message_content=InputTextMessageContent(message_text="فرمت صحیح: متن [کد_ایموجی]"),
                )
            ]
        preview = query[:50] + ("..." if len(query) > 50 else "")
        return [
            InlineQueryResultArticle(
                id="premium",
                title=f"ارسال با {len(entities)} ایموجی پرمیوم ✨",
                description=preview,
                input_message_content=InputTextMessageContent(message_text=text, entities=entities, parse_mode=None),
            )
        ]


class TelethonBridge:
    def __init__(self, client: TelegramClient) -> None:
        self.client = client

    async def start(self, bot_token: str) -> None:
        await self.client.start(bot_token=bot_token)

    async def stop(self) -> None:
        await self.client.disconnect()

    async def fetch_pack_documents(self, short_name: str):
        result = await self.client(
            functions.messages.GetStickerSetRequest(
                stickerset=types.InputStickerSetShortName(short_name=short_name),
                hash=0,
            )
        )
        return result.documents

    async def edit_inline_message(self, msg_id, text: str, entities: list):
        request = EditInlineBotMessageRequest(id=msg_id, message=text, entities=entities)
        dc_id = msg_id.dc_id
        if dc_id == self.client.session.dc_id:
            await self.client(request)
            return
        sender = await self.client._borrow_exported_sender(dc_id)
        try:
            await sender.send(request)
        finally:
            await self.client._return_exported_sender(sender)
