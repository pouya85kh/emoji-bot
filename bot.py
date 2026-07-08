import asyncio
import logging
import random
import re
import string
from datetime import datetime, timezone
from typing import Optional, Tuple, List

import aiosqlite
from aiogram import Bot, Dispatcher, F, Router, types
from aiogram.enums import ParseMode, ChatType
from aiogram.filters import Command, CommandObject, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.deep_linking import create_start_link

# ===================== CONFIG =====================
API_TOKEN = "7908572350:AAHenZ-AnqncC4OGwspRdEnSuJ3nWK33k3E"          # <= توکن ربات
ADMIN_IDS = {7049497099}              # آیدی عددی ادمین‌ها

# آیدی واقعی ایموجی‌های پرمیوم خود را جایگزین کنید
EMOJI = {
    "rocket":   5057918405923832965,
    "telegram": 5057918405923832965,
    "star":     5057918405923832965,
    "link":     5057918405923832965,
    "panel":    5057918405923832965,
    "help":     5057918405923832965,
    "mail":     5057918405923832965,
    "gem":      5057918405923832965,
    "bolt":     5057918405923832965,
    "note":     5057918405923832965,
    "mic":      5057918405923832965,
    "gift":     5057918405923832965,
    "chart":    5057918405923832965,
    "folder":   5057918405923832965,
    "check":    5057918405923832965,
    "gear":     5057918405923832965,
    "pencil":   5057918405923832965,
    "dino":     5057918405923832965,
    "ticket":   5057918405923832965,
    "back":     5057918405923832965,
}

FALLBACK = "\u2b50"               # ستاره معمولی به عنوان placeholder
PAGE_SIZE = 5
CHANNEL_MIN_MEMBERS = 50
PACK_LINK_RE = re.compile(r"(?:addemoji|addstickers)/([a-zA-Z0-9_]+)")
CODE_RE = re.compile(r"\[(\d+)\]")
DB_PATH = "bot.db"

# ===================== I18N =====================
TEXTS = {
    "fa": {
        "start_lang": "🌐 لطفاً زبان خود را انتخاب کنید:",
        "lang_set": "✅ زبان شما روی فارسی تنظیم شد.",
        "welcome": "{emoji_rocket} خوش آمدید {name}!\n\nبا این ربات می‌توانید ایموجی‌های پرمیوم را در هر چت تلگرام ارسال کنید.\nاز منوی زیر استفاده کنید:",
        "main_menu": "منوی اصلی",
        "btn_premium": "⭐ ایموجی پرمیوم",
        "btn_extract": "🔗 استخراج کد",
        "btn_account": "🖥 حساب من",
        "btn_help": "❓ راهنما",
        "btn_support": "✉️ پشتیبانی",
        "btn_admin": "⚙️ پنل مدیریت",
        "btn_back": "🔙 بازگشت",
        "my_emojis_title": "⭐ ایموجی‌های ذخیره‌شده: {current}/{limit}",
        "no_emoji": "هنوز ایموجی‌ای ذخیره نکردی.",
        "add_emoji_prompt": "✏️ ایموجی پرمیوم یا کد [ID] را بفرستید:",
        "ask_name": "🎙 لطفاً یک نام برای این ایموجی بفرستید (یا «پیش‌فرض» بفرستید):",
        "emoji_saved": "{emoji} «{name}» ذخیره شد ✅",
        "limit_reached": "⛔️ به سقف {limit} ایموجی رسیدی.",
        "set_link": "✅ ست شما آماده اشتراک شد!\nکد: {code}\nلینک: {link}",
        "set_invalid": "⚠️ کد ست معتبر نیست.",
        "set_added": "✅ {count} ایموجی به حساب شما اضافه شد.",
        "account_info": "💠 حساب کاربری\nآیدی: {uid}\nنام: {name}\nیوزرنیم: @{uname}\nوضعیت: {kind}\nایموجی: {cnt}/{limit}",
        "channel_list": "⌘ کانال‌های من\n\n{list}",
        "add_channel_guide": "برای افزودن کانال، ربات را ادمین کنید و آیدی یا یوزرنیم را بفرستید.\nحداقل عضو: {minmem}",
        "channel_added": "✅ کانال «{title}» ثبت شد.",
        "support_chat": "📨 پیام خود را بنویسید تا برای پشتیبانی ارسال شود:",
        "support_sent": "✅ پیام شما ارسال شد.",
        "ticket_sent": "✅ تیکت شما ثبت شد.",
        "help_text": "❓ راهنما\n\n1. برای ارسال ایموجی پرمیوم از حالت inline استفاده کنید.\n2. برای استخراج از پک، لینک را بفرستید.\n3. ایموجی‌های پرکاربرد را در «ایموجی‌های من» ذخیره کنید.\n\n💡 برای ساخت ایموجی پرمیوم می‌توانید از ربات @TgEmojis_bot کمک بگیرید.",
        "extract_menu": "📤 یک یا چند ایموجی پرمیوم بفرستید یا از لینک پک استفاده کنید.",
        "pack_extract_done": "✅ {cnt} ایموجی از پک «{name}» استخراج شد.",
        "broadcast_done": "📢 ارسال همگانی انجام شد.\nموفق: {ok} | ناموفق: {fail}",
        "admin_unlimited": "🔓 کاربر {uid} نامحدود شد.",
        # ... سایر کلیدها
    },
    "en": {
        "start_lang": "🌐 Please choose your language:",
        "lang_set": "✅ Language set to English.",
        "welcome": "{emoji_rocket} Welcome {name}!\n\nWith this bot you can send premium emojis in any Telegram chat.\nUse the menu below:",
        "main_menu": "Main Menu",
        "btn_premium": "⭐ Premium Emoji",
        "btn_extract": "🔗 Extract Code",
        "btn_account": "🖥 My Account",
        "btn_help": "❓ Help",
        "btn_support": "✉️ Support",
        "btn_admin": "⚙️ Admin Panel",
        "btn_back": "🔙 Back",
        "my_emojis_title": "⭐ Saved Emojis: {current}/{limit}",
        "no_emoji": "No emojis saved yet.",
        "add_emoji_prompt": "✏️ Send a premium emoji or [ID]:",
        "ask_name": "🎙 Please send a name for this emoji (or 'default'):",
        "emoji_saved": "{emoji} «{name}» saved ✅",
        "limit_reached": "⛔️ You have reached the limit of {limit} emojis.",
        "set_link": "✅ Your set is ready to share!\nCode: {code}\nLink: {link}",
        "set_invalid": "⚠️ Invalid set code.",
        "set_added": "✅ {count} emojis added to your account.",
        "account_info": "💠 Account\nID: {uid}\nName: {name}\nUsername: @{uname}\nStatus: {kind}\nEmojis: {cnt}/{limit}",
        "channel_list": "⌘ My Channels\n\n{list}",
        "add_channel_guide": "To add a channel, make the bot admin and send the ID or username.\nMin members: {minmem}",
        "channel_added": "✅ Channel «{title}» registered.",
        "support_chat": "📨 Write your message to be forwarded to support:",
        "support_sent": "✅ Your message was sent.",
        "ticket_sent": "✅ Your ticket was registered.",
        "help_text": "❓ Help\n\n1. Use inline mode to send premium emojis.\n2. Send a pack link to extract codes.\n3. Save frequently used emojis in 'My Emojis'.\n\n💡 To create premium emojis, you can use @TgEmojis_bot .",
        "extract_menu": "📤 Send one or more premium emojis or use a pack link.",
        "pack_extract_done": "✅ {cnt} emojis extracted from pack «{name}».",
        "broadcast_done": "📢 Broadcast finished.\nSuccess: {ok} | Failed: {fail}",
        "admin_unlimited": "🔓 User {uid} is now unlimited.",
        # ... etc
    }
}

# کمک‌کننده: جایگذاری ایموجی پرمیوم در متن
def _p(key: str) -> str:
    """Returns the placeholder string for a premium emoji, to be later replaced with entity."""
    return f"{{{key}}}"

def apply_emoji(text: str) -> Tuple[str, list]:
    """Replace all {key} placeholders with custom emoji entities."""
    entities = []
    for key, eid in EMOJI.items():
        placeholder = _p(key)
        while placeholder in text:
            idx = text.find(placeholder)
            ent = MessageEntityCustomEmoji(
                offset=len(text[:idx].encode("utf-16-le")) // 2,
                length=1,
                document_id=eid
            )
            text = text[:idx] + FALLBACK + text[idx+len(placeholder):]
            entities.append(ent)
    return text, entities

def _t(lang: str, key: str, **kwargs) -> str:
    """Get translated string with optional formatting."""
    base = TEXTS.get(lang, TEXTS["fa"]).get(key, key)
    return base.format(**kwargs) if kwargs else base

# ===================== DATABASE =====================
async def get_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
        return await cur.fetchone()

async def ensure_user(user_id: int, first_name: str = None, username: str = None, lang: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        row = await get_user(user_id)
        if not row:
            now = datetime.now(timezone.utc).isoformat()
            await db.execute(
                "INSERT INTO users(user_id, first_name, username, lang, joined_at) VALUES(?,?,?,?,?)",
                (user_id, first_name, username, lang, now)
            )
        else:
            updates = []
            params = []
            if first_name and first_name != row["first_name"]:
                updates.append("first_name=?")
                params.append(first_name)
            if username and username != row["username"]:
                updates.append("username=?")
                params.append(username)
            if lang and lang != row.get("lang"):
                updates.append("lang=?")
                params.append(lang)
            if updates:
                params.append(user_id)
                await db.execute(f"UPDATE users SET {','.join(updates)} WHERE user_id=?", params)
        await db.commit()

async def user_emoji_count(user_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT COUNT(*) as cnt FROM saved_emojis WHERE user_id=?", (user_id,))
        row = await cur.fetchone()
        return row["cnt"]

async def user_limit(user_id: int):
    u = await get_user(user_id)
    if not u:
        return 50
    if u["unlimited"]:
        return None
    return u["emoji_limit"]

async def add_saved_emoji(user_id: int, name: str, doc_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        limit = await user_limit(user_id)
        cnt = await user_emoji_count(user_id)
        if limit is not None and cnt >= limit:
            return False
        await db.execute("INSERT INTO saved_emojis(user_id, name, doc_id) VALUES(?,?,?)",
                         (user_id, name, doc_id))
        await db.commit()
        return True

async def list_saved_emojis(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM saved_emojis WHERE user_id=? ORDER BY id", (user_id,))
        return await cur.fetchall()

async def delete_saved_emoji(row_id: int, user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM saved_emojis WHERE id=? AND user_id=?", (row_id, user_id))
        await db.commit()

async def get_or_create_set_code(user_id: int) -> str:
    u = await get_user(user_id)
    if u and u["set_code"]:
        return u["set_code"]
    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=7))
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET set_code=? WHERE user_id=?", (code, user_id))
        await db.commit()
    return code

async def find_user_by_set_code(code: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM users WHERE set_code=?", (code,))
        return await cur.fetchone()

async def add_channel(user_id: int, channel_id: int, title: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT id FROM channels WHERE channel_id=?", (str(channel_id),))
        if await cur.fetchone():
            return False
        await db.execute("INSERT INTO channels(user_id, channel_id, title) VALUES(?,?,?)",
                         (user_id, str(channel_id), title))
        await db.commit()
        return True

async def list_channels(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM channels WHERE user_id=?", (user_id,))
        return await cur.fetchall()

async def is_registered_channel(channel_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT id FROM channels WHERE channel_id=?", (str(channel_id),))
        return (await cur.fetchone()) is not None

async def add_ticket(user_id: int, message: str):
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO tickets(user_id, message, status, created_at) VALUES(?,?,?,?)",
                         (user_id, message, "open", now))
        await db.commit()

async def stats():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT COUNT(*) as c FROM users")
        users_count = (await cur.fetchone())["c"]
        cur = await db.execute("SELECT COUNT(*) as c FROM saved_emojis")
        emojis = (await cur.fetchone())["c"]
        cur = await db.execute("SELECT COUNT(*) as c FROM channels")
        channels = (await cur.fetchone())["c"]
        cur = await db.execute("SELECT COUNT(*) as c FROM tickets WHERE status='open'")
        tickets = (await cur.fetchone())["c"]
        cur = await db.execute("SELECT COUNT(*) as c FROM users WHERE unlimited=1")
        unlim = (await cur.fetchone())["c"]
        return {"users": users_count, "emojis": emojis, "channels": channels, "open_tickets": tickets, "unlimited": unlim}

async def all_user_ids():
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT user_id FROM users")
        rows = await cur.fetchall()
        return [r[0] for r in rows]

# ===================== FSM States =====================
class LangSelect(StatesGroup):
    choosing = State()

class AddEmoji(StatesGroup):
    waiting_id = State()
    waiting_name = State()

class SupportChat(StatesGroup):
    msg = State()

class SupportTicket(StatesGroup):
    ticket = State()

class AdminUnlimit(StatesGroup):
    uid = State()

class AdminBroadcast(StatesGroup):
    msg = State()

class ChannelAdd(StatesGroup):
    username = State()

# ===================== ROUTER & HANDLERS =====================
router = Router()

# --- Helpers for keyboards ---
def main_menu_kb(lang: str, user_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=f"⭐ {_t(lang, 'btn_premium')}", callback_data="menu_premium"),
        InlineKeyboardButton(text=f"🔗 {_t(lang, 'btn_extract')}", callback_data="menu_extract")
    )
    builder.row(
        InlineKeyboardButton(text=f"🖥 {_t(lang, 'btn_account')}", callback_data="menu_account"),
        InlineKeyboardButton(text=f"❓ {_t(lang, 'btn_help')}", callback_data="menu_help")
    )
    builder.row(
        InlineKeyboardButton(text=f"✉️ {_t(lang, 'btn_support')}", callback_data="menu_support")
    )
    if user_id in ADMIN_IDS:
        builder.row(InlineKeyboardButton(text=f"⚙️ {_t(lang, 'btn_admin')}", callback_data="admin_panel"))
    return builder.as_markup()

def account_menu_kb(lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=f"⭐ {_t(lang, 'my_emojis')}", callback_data="my_emojis"),
        InlineKeyboardButton(text=f"📊 {_t(lang, 'my_stats')}", callback_data="my_stats")
    )
    builder.row(
        InlineKeyboardButton(text=f"📋 {_t(lang, 'channels')}", callback_data="menu_channels"),
        InlineKeyboardButton(text=f"⭐ {_t(lang, 'my_set')}", callback_data="my_set")
    )
    builder.row(
        InlineKeyboardButton(text=f"🌐 {_t(lang, 'change_lang')}", callback_data="change_lang")
    )
    builder.row(InlineKeyboardButton(text=f"🔙 {_t(lang, 'btn_back')}", callback_data="back_main"))
    return builder.as_markup()

def my_emojis_kb(rows, page: int, total_pages: int, lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for r in rows:
        # دکمه اسم ایموجی (نمی‌توان خود ایموجی پرمیوم را نشان داد)
        builder.row(InlineKeyboardButton(text=r["name"], callback_data="noop"),
                    InlineKeyboardButton(text="🗑", callback_data=f"delemoji_{r['id']}"))
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"emojipage_{page-1}"))
    nav_buttons.append(InlineKeyboardButton(text=f"{page+1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"emojipage_{page+1}"))
    builder.row(*nav_buttons)
    builder.row(InlineKeyboardButton(text=f"✏️ {_t(lang, 'add_emoji_prompt')}", callback_data="add_emoji_start"))
    builder.row(InlineKeyboardButton(text=f"🔙 {_t(lang, 'btn_back')}", callback_data="menu_account"))
    return builder.as_markup()

# --- Command /start ---
@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext, command: CommandObject, bot: Bot):
    user = message.from_user
    u = await get_user(user.id)
    if u is None or u["lang"] is None:
        # No language set yet
        await state.set_state(LangSelect.choosing)
        await state.update_data(deep_link=command.args)
        kb = InlineKeyboardBuilder()
        kb.row(InlineKeyboardButton(text="🇮🇷 فارسی", callback_data="lang_fa"),
               InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en"))
        await message.answer(_t("fa", "start_lang"), reply_markup=kb.as_markup())
        return
    lang = u["lang"]
    await state.clear()
    # Process deep link
    args = command.args
    if args and args.startswith("set_"):
        code = args[4:]
        owner = await find_user_by_set_code(code)
        if not owner:
            await message.answer(_t(lang, "set_invalid"))
        else:
            cnt = 0
            limit = await user_limit(user.id)
            async with aiosqlite.connect(DB_PATH) as db:
                cur = await db.execute("SELECT doc_id, name FROM saved_emojis WHERE user_id=?", (owner["user_id"],))
                src = await cur.fetchall()
                for em in src:
                    if limit is not None and await user_emoji_count(user.id) >= limit:
                        break
                    await db.execute("INSERT INTO saved_emojis(user_id, name, doc_id) VALUES(?,?,?)",
                                     (user.id, em["name"], em["doc_id"]))
                    cnt += 1
                await db.commit()
            await message.answer(_t(lang, "set_added", count=cnt))
        return
    # Show main menu
    await show_main_menu(message, lang)

async def show_main_menu(msg: Message, lang: str):
    text_raw = _t(lang, "welcome", name=msg.from_user.first_name or "", emoji_rocket=_p("rocket"))
    text, entities = apply_emoji(text_raw)
    await msg.answer(text, reply_markup=main_menu_kb(lang, msg.from_user.id), entities=entities)

# --- Language selection callback ---
@router.callback_query(F.data.startswith("lang_"), LangSelect.choosing)
async def lang_chosen(callback: CallbackQuery, state: FSMContext, bot: Bot):
    lang = callback.data.split("_")[1]  # 'fa' or 'en'
    await ensure_user(callback.from_user.id, callback.from_user.first_name, callback.from_user.username, lang)
    data = await state.get_data()
    deep_link = data.get("deep_link")
    await state.clear()
    await callback.answer()
    await callback.message.answer(_t(lang, "lang_set"))
    # process deep link if any
    if deep_link and deep_link.startswith("set_"):
        code = deep_link[4:]
        owner = await find_user_by_set_code(code)
        if owner:
            cnt = 0
            limit = await user_limit(callback.from_user.id)
            async with aiosqlite.connect(DB_PATH) as db:
                cur = await db.execute("SELECT doc_id, name FROM saved_emojis WHERE user_id=?", (owner["user_id"],))
                src = await cur.fetchall()
                for em in src:
                    if limit is not None and await user_emoji_count(callback.from_user.id) >= limit:
                        break
                    await db.execute("INSERT INTO saved_emojis(user_id, name, doc_id) VALUES(?,?,?)",
                                     (callback.from_user.id, em["name"], em["doc_id"]))
                    cnt += 1
                await db.commit()
            await callback.message.answer(_t(lang, "set_added", count=cnt))
        else:
            await callback.message.answer(_t(lang, "set_invalid"))
    await show_main_menu(callback.message, lang)
    await callback.message.delete()

# --- Main menu callback ---
@router.callback_query(F.data == "back_main")
async def back_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    lang = (await get_user(callback.from_user.id))["lang"]
    text_raw = _t(lang, "main_menu")
    text, entities = apply_emoji(f"{_p('rocket')} " + text_raw)
    await callback.message.edit_text(text, reply_markup=main_menu_kb(lang, callback.from_user.id), entities=entities)
    await callback.answer()

# --- Account ---
@router.callback_query(F.data == "menu_account")
async def account(callback: CallbackQuery):
    u = await get_user(callback.from_user.id)
    lang = u["lang"]
    limit = await user_limit(callback.from_user.id)
    cnt = await user_emoji_count(callback.from_user.id)
    kind = _t(lang, "unlimited_user") if u["unlimited"] else _t(lang, "normal_user")
    text_raw = _t(lang, "account_info",
                  uid=callback.from_user.id,
                  name=callback.from_user.first_name or "-",
                  uname=callback.from_user.username or "-",
                  kind=kind,
                  cnt=cnt,
                  limit=limit if limit is not None else _t(lang, "unlimited"))
    text, entities = apply_emoji(f"{_p('panel')} " + text_raw)
    await callback.message.edit_text(text, reply_markup=account_menu_kb(lang), entities=entities)
    await callback.answer()

# --- Change language ---
@router.callback_query(F.data == "change_lang")
async def change_lang(callback: CallbackQuery, state: FSMContext):
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🇮🇷 فارسی", callback_data="lang_fa"),
           InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en"))
    await callback.message.edit_text(_t("fa", "start_lang"), reply_markup=kb.as_markup())
    await state.set_state(LangSelect.choosing)
    await callback.answer()

# --- My Emojis (paginated) ---
@router.callback_query(F.data == "my_emojis")
async def my_emojis(callback: CallbackQuery):
    await show_emojis_page(callback.message, callback.from_user.id, 0, edit=True)
    await callback.answer()

@router.callback_query(F.data.startswith("emojipage_"))
async def emojipage(callback: CallbackQuery):
    page = int(callback.data.split("_")[1])
    await show_emojis_page(callback.message, callback.from_user.id, page, edit=True)
    await callback.answer()

async def show_emojis_page(msg: Message, user_id: int, page: int, edit: bool = False):
    u = await get_user(user_id)
    lang = u["lang"]
    rows = await list_saved_emojis(user_id)
    total = len(rows)
    limit = await user_limit(user_id)
    limit_str = str(limit) if limit else _t(lang, "unlimited")
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(0, min(page, total_pages - 1))
    page_rows = rows[page*PAGE_SIZE : (page+1)*PAGE_SIZE]
    text_raw = _t(lang, "my_emojis_title", current=total, limit=limit_str)
    if not page_rows:
        text_raw += "\n" + _t(lang, "no_emoji")
    text, entities = apply_emoji(f"{_p('star')} " + text_raw)
    kb = my_emojis_kb(page_rows, page, total_pages, lang)
    if edit:
        await msg.edit_text(text, reply_markup=kb, entities=entities)
    else:
        await msg.answer(text, reply_markup=kb, entities=entities)

# --- Add emoji FSM ---
@router.callback_query(F.data == "add_emoji_start")
async def add_emoji_start(callback: CallbackQuery, state: FSMContext):
    u = await get_user(callback.from_user.id)
    lang = u["lang"]
    limit = await user_limit(callback.from_user.id)
    if limit is not None and await user_emoji_count(callback.from_user.id) >= limit:
        await callback.answer(_t(lang, "limit_reached", limit=limit), show_alert=True)
        return
    await state.set_state(AddEmoji.waiting_id)
    await callback.message.edit_text(_t(lang, "add_emoji_prompt"),
                                     reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                                         [InlineKeyboardButton(text=_t(lang, "btn_back"), callback_data="my_emojis")]
                                     ]))
    await callback.answer()

@router.message(AddEmoji.waiting_id, F.content_type.in_({"text", "animation", "sticker"}))
async def emoji_id_received(message: Message, state: FSMContext):
    # extract doc_id from entities or text pattern
    doc_ids = []
    if message.entities:
        for ent in message.entities:
            if isinstance(ent, MessageEntityCustomEmoji):
                doc_ids.append(ent.document_id)
    if not doc_ids:
        # try parse [id] from text
        doc_ids = [int(m.group(1)) for m in CODE_RE.finditer(message.text or "")]
    if not doc_ids:
        await message.answer("⚠️ ایموجی پرمیوم یا کد معتبری پیدا نشد.")
        return
    doc_id = doc_ids[0]
    await state.update_data(doc_id=doc_id)
    await state.set_state(AddEmoji.waiting_name)
    # show current emoji list as context
    u = await get_user(message.from_user.id)
    lang = u["lang"]
    rows = await list_saved_emojis(message.from_user.id)
    # simple list
    list_text = "\n".join(f"⭐ {r['name']}" for r in rows) if rows else _t(lang, "no_emoji")
    await message.answer(f"{_t(lang, 'ask_name')}\n\n{list_text}")

@router.message(AddEmoji.waiting_name)
async def emoji_name_received(message: Message, state: FSMContext):
    data = await state.get_data()
    doc_id = data["doc_id"]
    lang = (await get_user(message.from_user.id))["lang"]
    name = message.text.strip() or f"Emoji #{doc_id}"
    if name.lower() in ("پیش‌فرض", "default"):
        name = f"Emoji #{doc_id}"
    success = await add_saved_emoji(message.from_user.id, name, doc_id)
    if not success:
        limit = await user_limit(message.from_user.id)
        await message.answer(_t(lang, "limit_reached", limit=limit))
    else:
        # Build text with the emoji entity
        text_raw = _t(lang, "emoji_saved", emoji=FALLBACK, name=name)
        entities = [MessageEntityCustomEmoji(offset=0, length=1, document_id=doc_id)]
        await message.answer(text_raw, entities=entities,
                             reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                                 [InlineKeyboardButton(text=_t(lang, "my_emojis"), callback_data="my_emojis")]
                             ]))
    await state.clear()

# --- Delete emoji ---
@router.callback_query(F.data.startswith("delemoji_"))
async def del_emoji(callback: CallbackQuery):
    emoji_id = int(callback.data.split("_")[1])
    await delete_saved_emoji(emoji_id, callback.from_user.id)
    await show_emojis_page(callback.message, callback.from_user.id, 0, edit=True)
    await callback.answer("🗑 حذف شد")

# --- My Stats ---
@router.callback_query(F.data == "my_stats")
async def my_stats(callback: CallbackQuery):
    u = await get_user(callback.from_user.id)
    lang = u["lang"]
    cnt = await user_emoji_count(callback.from_user.id)
    ch_cnt = len(await list_channels(callback.from_user.id))
    text = f"📊 {_t(lang, 'my_stats')}\n\n⭐ {cnt}\n📋 {ch_cnt}"
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text=_t(lang, "btn_back"), callback_data="menu_account"))
    await callback.message.edit_text(text, reply_markup=kb.as_markup())
    await callback.answer()

# --- My Set (sharing) ---
@router.callback_query(F.data == "my_set")
async def my_set(callback: CallbackQuery):
    lang = (await get_user(callback.from_user.id))["lang"]
    code = await get_or_create_set_code(callback.from_user.id)
    me = await callback.bot.get_me()
    link = create_start_link(me.username, f"set_{code}")
    text_raw = _t(lang, "set_link", code=code, link=link)
    text, entities = apply_emoji(f"{_p('check')} " + text_raw)
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="📋 Copy Link", callback_data=f"copy_{code}"))
    kb.row(InlineKeyboardButton(text=_t(lang, "btn_back"), callback_data="menu_account"))
    await callback.message.edit_text(text, reply_markup=kb.as_markup(), entities=entities)
    await callback.answer()

@router.callback_query(F.data.startswith("copy_"))
async def copy_link(callback: CallbackQuery):
    code = callback.data.split("_")[1]
    me = await callback.bot.get_me()
    link = create_start_link(me.username, f"set_{code}")
    await callback.answer(f"Link: {link}", show_alert=True)

# --- Channels ---
@router.callback_query(F.data == "menu_channels")
async def menu_channels(callback: CallbackQuery):
    lang = (await get_user(callback.from_user.id))["lang"]
    chans = await list_channels(callback.from_user.id)
    if not chans:
        clist = _t(lang, "no_channel")
    else:
        clist = "\n".join(f"📋 {c['title']}" for c in chans)
    text = f"{_p('folder')} {_t(lang, 'channel_list', list=clist)}"
    text, entities = apply_emoji(text)
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text=f"✏️ {_t(lang, 'add_channel')}", callback_data="add_channel_start"))
    kb.row(InlineKeyboardButton(text=_t(lang, "btn_back"), callback_data="menu_account"))
    await callback.message.edit_text(text, reply_markup=kb.as_markup(), entities=entities)
    await callback.answer()

@router.callback_query(F.data == "add_channel_start")
async def add_channel_start(callback: CallbackQuery, state: FSMContext):
    lang = (await get_user(callback.from_user.id))["lang"]
    await state.set_state(ChannelAdd.username)
    text = _t(lang, "add_channel_guide", minmem=CHANNEL_MIN_MEMBERS)
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=_t(lang, "btn_back"), callback_data="menu_channels")]
    ]))
    await callback.answer()

@router.message(ChannelAdd.username)
async def channel_username_received(message: Message, state: FSMContext, bot: Bot):
    raw = message.text.strip()
    try:
        chat = await bot.get_chat(raw)
    except Exception as e:
        await message.answer(f"❌ Error: {e}")
        return
    if chat.type not in ("channel", "supergroup"):
        await message.answer("⚠️ Not a channel.")
        return
    # Check member count and admin rights
    if chat.type == "channel":
        member_count = await chat.get_member_count()
        if member_count < CHANNEL_MIN_MEMBERS:
            await message.answer(f"Minimum {CHANNEL_MIN_MEMBERS} members required.")
            return
    # Check bot is admin with edit rights
    me = await bot.get_me()
    try:
        my_member = await chat.get_member(me.id)
        if not (my_member.is_chat_admin() and my_member.can_edit_messages):
            await message.answer("I need to be admin with edit messages permission.")
            return
    except:
        await message.answer("Cannot check permissions. Make me admin with edit rights.")
        return
    ok = await add_channel(message.from_user.id, chat.id, chat.title or chat.username or str(chat.id))
    lang = (await get_user(message.from_user.id))["lang"]
    if not ok:
        await message.answer("Already registered.")
    else:
        await message.answer(_t(lang, "channel_added", title=chat.title))
    await state.clear()

# --- Channel auto-edit ---
@router.message(F.chat.type.in_({"channel", "supergroup"}), F.text.contains("["))
async def channel_auto_edit(message: Message, bot: Bot):
    if not await is_registered_channel(message.chat.id):
        return
    text = message.text or message.caption or ""
    matches = list(CODE_RE.finditer(text))
    if not matches:
        return
    # build text with custom emoji entities
    entities = []
    new_text = ""
    last = 0
    for m in matches:
        new_text += text[last:m.start()]
        ent = MessageEntityCustomEmoji(
            offset=len(new_text.encode("utf-16-le")) // 2,
            length=1,
            document_id=int(m.group(1))
        )
        new_text += FALLBACK
        entities.append(ent)
        last = m.end()
    new_text += text[last:]
    try:
        await bot.edit_message_text(chat_id=message.chat.id, message_id=message.message_id,
                                    text=new_text, entities=entities)
    except Exception as e:
        logging.error(f"Channel edit failed: {e}")

# --- Premium Emoji (inline mode) ---
@router.inline_query()
async def inline_query(inline_query: InlineQuery):
    query = inline_query.query.strip()
    if not query:
        results = [
            InlineQueryResultArticle(
                id="1",
                title="✨ Send premium emoji",
                description="Write text and insert [emoji_id]",
                input_message_content=InputTextMessageContent(message_text="Example: hello [1234567890]")
            )
        ]
        await inline_query.answer(results, cache_time=0, is_personal=True)
        return
    # Build final message from query
    text, entities = parse_inline_text(query)
    if not entities:
        results = [
            InlineQueryResultArticle(
                id="2",
                title="⚠️ Invalid format",
                description="Use [ID] to insert a premium emoji",
                input_message_content=InputTextMessageContent(message_text=query)
            )
        ]
        await inline_query.answer(results, cache_time=0, is_personal=True)
        return
    results = [
        InlineQueryResultArticle(
            id="3",
            title=f"Send with {len(entities)} premium emoji(s) ✨",
            input_message_content=InputTextMessageContent(message_text=text, entities=entities),
            description=text[:50]
        )
    ]
    await inline_query.answer(results, cache_time=0, is_personal=True)

def parse_inline_text(query: str) -> Tuple[str, list]:
    matches = list(CODE_RE.finditer(query))
    if not matches:
        return query, []
    new_text = ""
    entities = []
    last = 0
    for m in matches:
        new_text += query[last:m.start()]
        ent = MessageEntityCustomEmoji(
            offset=len(new_text.encode("utf-16-le")) // 2,
            length=1,
            document_id=int(m.group(1))
        )
        new_text += FALLBACK
        entities.append(ent)
        last = m.end()
    new_text += query[last:]
    return new_text, entities

# --- Extract Code (send emoji or pack link) ---
@router.callback_query(F.data == "menu_extract")
async def extract_menu(callback: CallbackQuery):
    lang = (await get_user(callback.from_user.id))["lang"]
    text = _t(lang, "extract_menu")
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text=f"🎁 {_t(lang, 'from_pack')}", callback_data="extract_pack"))
    kb.row(InlineKeyboardButton(text=_t(lang, "btn_back"), callback_data="back_main"))
    await callback.message.edit_text(text, reply_markup=kb.as_markup())
    await callback.answer()

@router.callback_query(F.data == "extract_pack")
async def extract_pack(callback: CallbackQuery):
    await callback.message.edit_text("لینک پک را بفرستید (addemoji/...):")
    # We'll just wait for a message, but to keep simple we can just reply to next message
    # Instead, let's use a temporary state
    # Not using FSM for simplicity, but can be added
    pass

# ... (many more handlers for support, admin, etc.)

# ===================== MAIN =====================
async def main():
    logging.basicConfig(level=logging.INFO)
    # ensure tables
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                first_name TEXT,
                username TEXT,
                emoji_limit INTEGER DEFAULT 50,
                unlimited INTEGER DEFAULT 0,
                set_code TEXT,
                lang TEXT DEFAULT 'fa',
                joined_at TEXT
            );
            CREATE TABLE IF NOT EXISTS saved_emojis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                name TEXT,
                doc_id INTEGER
            );
            CREATE TABLE IF NOT EXISTS channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                channel_id TEXT,
                title TEXT
            );
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                message TEXT,
                status TEXT DEFAULT 'open',
                created_at TEXT
            );
        """)
        await db.commit()

    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    bot = Bot(token=API_TOKEN, parse_mode=ParseMode.HTML)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
