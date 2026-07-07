import os
import re
import json
import sqlite3
import random
import string
from datetime import datetime
from typing import Dict, Any, List

from aiogram import Bot, Dispatcher, F, types
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    Message,
    CallbackQuery,
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent,
    MessageEntity
)
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

# ================= تنظیمات و محیط =================
BOT_TOKEN = os.environ["BOT_TOKEN"]
ADMIN_IDS = {7049497099}  # آیدی عددی ادمین‌ها
SUPPORT_USERNAME = "nooooofear"

FALLBACK_EMOJI = "⭐"
DEFAULT_EMOJI_LIMIT = 50
CHANNEL_MIN_MEMBERS = 50

PACK_LINK_RE = re.compile(r"(?:addemoji|addstickers)/([a-zA-Z0-9_]+)")
CODE_RE = re.compile(r"\[(\d+)\]")
DB_PATH = os.environ.get("DB_PATH", "bot.db")

# آیدی ایموجی‌های دکوراتور برای رنگی‌سازی منوها مطابق تصاویر ارسالی
# در صورت نیاز می‌توانید با آیدی‌های دلخواه جایگزین کنید
DECO_EMOJI_ID = "5057918405923832965" 

EMOJI_IDS = {
    "rocket": DECO_EMOJI_ID,
    "telegram": DECO_EMOJI_ID,
    "star": DECO_EMOJI_ID,
    "link": DECO_EMOJI_ID,
    "panel": DECO_EMOJI_ID,
    "help": DECO_EMOJI_ID,
    "mail": DECO_EMOJI_ID,
    "gem": DECO_EMOJI_ID,
    "bolt": DECO_EMOJI_ID,
    "note": DECO_EMOJI_ID,
    "mic": DECO_EMOJI_ID,
    "gift": DECO_EMOJI_ID,
    "chart": DECO_EMOJI_ID,
    "folder": DECO_EMOJI_ID,
    "check": DECO_EMOJI_ID,
    "gear": DECO_EMOJI_ID,
    "pencil": DECO_EMOJI_ID,
    "dino": DECO_EMOJI_ID,
    "ticket": DECO_EMOJI_ID,
    "back": DECO_EMOJI_ID,
    "lang": DECO_EMOJI_ID,
    "trash": DECO_EMOJI_ID
}

# ================= دیتابیس SQLITE =================
_conn = sqlite3.connect(DB_PATH, check_same_thread=False)
_conn.row_factory = sqlite3.Row

def db_init():
    cur = _conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users(
        user_id INTEGER PRIMARY KEY,
        first_name TEXT,
        username TEXT,
        emoji_limit INTEGER DEFAULT 50,
        unlimited INTEGER DEFAULT 0,
        set_code TEXT,
        joined_at TEXT
    );
    """)
    _conn.commit()

    # رفع مشکل نبودن ستون زبان در نسخه‌های قدیمی دیتابیس
    try:
        cur.execute("ALTER TABLE users ADD COLUMN lang TEXT;")
        _conn.commit()
    except sqlite3.OperationalError:
        pass

    cur.execute("""
    CREATE TABLE IF NOT EXISTS saved_emojis(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        name TEXT,
        doc_id TEXT
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS channels(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        channel_id TEXT,
        title TEXT
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS tickets(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        message TEXT,
        status TEXT DEFAULT 'open',
        created_at TEXT
    );
    """)
    _conn.commit()

db_init()

def ensure_user(user_id: int, first_name: str = None, username: str = None):
    cur = _conn.cursor()
    cur.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    if row is None:
        cur.execute(
            "INSERT INTO users(user_id, first_name, username, emoji_limit, unlimited, lang, joined_at) VALUES(?,?,?,?,?,?,?)",
            (user_id, first_name, username, DEFAULT_EMOJI_LIMIT, 0, 'fa', datetime.utcnow().isoformat()),
        )
        _conn.commit()
    else:
        cur.execute("UPDATE users SET first_name=?, username=? WHERE user_id=?", (first_name, username, user_id))
        _conn.commit()

def get_user(user_id: int):
    cur = _conn.cursor()
    cur.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    if row is None:
        return None
    return dict(row)

def set_user_lang(user_id: int, lang: str):
    cur = _conn.cursor()
    cur.execute("UPDATE users SET lang=? WHERE user_id=?", (lang, user_id))
    _conn.commit()

def user_emoji_count(user_id: int) -> int:
    cur = _conn.cursor()
    cur.execute("SELECT COUNT(*) c FROM saved_emojis WHERE user_id=?", (user_id,))
    return cur.fetchone()["c"]

def user_limit(user_id: int):
    u = get_user(user_id)
    if u is None:
        return DEFAULT_EMOJI_LIMIT
    if u["unlimited"]:
        return None
    return u["emoji_limit"]

def add_saved_emoji(user_id: int, name: str, doc_id: str):
    cur = _conn.cursor()
    cur.execute("INSERT INTO saved_emojis(user_id, name, doc_id) VALUES(?,?,?)", (user_id, name, str(doc_id)))
    _conn.commit()

def list_saved_emojis(user_id: int):
    cur = _conn.cursor()
    cur.execute("SELECT * FROM saved_emojis WHERE user_id=? ORDER BY id", (user_id,))
    return cur.fetchall()

def delete_saved_emoji(row_id: int, user_id: int):
    cur = _conn.cursor()
    cur.execute("DELETE FROM saved_emojis WHERE id=? AND user_id=?", (row_id, user_id))
    _conn.commit()

def get_or_create_set_code(user_id: int) -> str:
    u = get_user(user_id)
    if u and u["set_code"]:
        return u["set_code"]
    code = "".join(random.choices(string.ascii_uppercase + string.digits, k=7))
    cur = _conn.cursor()
    cur.execute("UPDATE users SET set_code=? WHERE user_id=?", (code, user_id))
    _conn.commit()
    return code

def find_user_by_set_code(code: str):
    cur = _conn.cursor()
    cur.execute("SELECT * FROM users WHERE set_code=?", (code,))
    row = cur.fetchone()
    return dict(row) if row else None

def add_channel(user_id: int, channel_id: int, title: str) -> bool:
    cur = _conn.cursor()
    cur.execute("SELECT id FROM channels WHERE channel_id=?", (str(channel_id),))
    if cur.fetchone():
        return False
    cur.execute("INSERT INTO channels(user_id, channel_id, title) VALUES(?,?,?)", (user_id, str(channel_id), title))
    _conn.commit()
    return True

def list_channels(user_id: int):
    cur = _conn.cursor()
    cur.execute("SELECT * FROM channels WHERE user_id=?", (user_id,))
    return cur.fetchall()

def is_registered_channel(channel_id: int):
    cur = _conn.cursor()
    cur.execute("SELECT * FROM channels WHERE channel_id=?", (str(channel_id),))
    return cur.fetchone()

def add_ticket(user_id: int, message: str):
    cur = _conn.cursor()
    cur.execute(
        "INSERT INTO tickets(user_id, message, status, created_at) VALUES(?,?,?,?)",
        (user_id, message, "open", datetime.utcnow().isoformat()),
    )
    _conn.commit()

def db_stats():
    cur = _conn.cursor()
    cur.execute("SELECT COUNT(*) c FROM users")
    u_count = cur.fetchone()["c"]
    cur.execute("SELECT COUNT(*) c FROM saved_emojis")
    e_count = cur.fetchone()["c"]
    cur.execute("SELECT COUNT(*) c FROM channels")
    c_count = cur.fetchone()["c"]
    cur.execute("SELECT COUNT(*) c FROM tickets WHERE status='open'")
    o_tickets = cur.fetchone()["c"]
    cur.execute("SELECT COUNT(*) c FROM users WHERE unlimited=1")
    unlim = cur.fetchone()["c"]
    return {"users": u_count, "emojis": e_count, "channels": c_count, "open_tickets": o_tickets, "unlimited_users": unlim}

def all_user_ids():
    cur = _conn.cursor()
    cur.execute("SELECT user_id FROM users")
    return [r["user_id"] for r in cur.fetchall()]


# ================= ترجمه و محلی‌سازی (Localization) =================
STRINGS = {
    "fa": {
        "welcome": "خوش آمدید {}!\n─\nبا این ربات می‌توانید ایموجی‌های پرمیوم را در هر چتی ارسال کنید.\nمنوی زیر را انتخاب کنید:",
        "menu_premium": "🔮 ارسال ایموجی پرمیوم",
        "menu_extract": "📥 استخراج کد ایموجی",
        "menu_account": "👤 حساب من",
        "menu_help": "📚 راهنما",
        "menu_support": "📞 پشتیبانی",
        "admin_panel": "🛠 پنل مدیریت",
        "back": "🔙 بازگشت",
        "lang_select": "🌐 لطفا زبان خود را انتخاب کنید / Please select your language:",
        "invalid_set": "⚠️ کد ست معتبر نیست یا منقضی شده.",
        "set_added": "✅ {} ایموجی از ست دریافتی به حساب شما اضافه شد.",
        "premium_section": "✨ ارسال ایموجی پرمیوم\n─\nیک پیام جدید در همین چت بفرستید:\n⚡ چند ایموجی پرمیوم بفرستید یا کد عددی وارد کنید:\n`[5792080508976373427]`",
        "inline_btn": "✨ رفتن به حالت اینلاین",
        "extract_section": "📤 استخراج کد ایموجی پرمیوم\n─\nیک یا چند ایموجی پرمیوم برای من بفرستید یا از دکمه زیر استفاده کنید:",
        "extract_pack_btn": "🎁 استخراج از لینک پک",
        "await_pack": "🎁 لینک پک ایموجی پرمیوم را بفرستید:\nمثال: `https://t.me/addemoji/PackName`",
        "invalid_pack": "⚠️ لینک معتبر پک ایموجی نیست.",
        "fetching_pack": "⏳ در حال دریافت پک...",
        "pack_empty": "⚠️ پک خالی است یا معتبر نیست.",
        "pack_success": "✅ استخراج {} ایموجی از پک انجام شد.",
        "my_emojis_title": "⭐ ایموجی‌های ذخیره‌شده: {}/{}",
        "no_emojis": "هنوز ایموجی‌ای ذخیره نکردید.",
        "add_emoji_btn": "➕ افزودن ایموجی جدید",
        "limit_reached": "⛔️ به سقف ذخیره‌سازی رسیده‌اید.",
        "send_emoji_prompt": "✏️ حالا خود ایموجی پرمیوم مورد نظر یا کد آن را بفرستید:",
        "send_name_prompt": "🎙 ابتدا یک اسم دلخواه برای این ایموجی بفرستید:",
        "saved_success": "«{}» ذخیره شد ✅",
        "account_txt": "💠 حساب کاربری شما\n─\n◁ آیدی: {}\n◁ نام: {}\n◁ زبان: {}\n◁ نوع کاربری: {}\n📈 ذخیره‌شده: {}/{}",
        "stats_btn": "📊 آمار من",
        "set_btn": "🔗 اشتراک ست من",
        "change_lang_btn": "🌐 تغییر زبان / Change Lang",
        "my_stats_txt": "📊 آمار شما\n─\n⭐ تعداد ایموجی: {}\n📋 تعداد کانال‌ها: {}",
        "my_set_txt": "✅ ست شما آماده اشتراک شد!\n─\n◁ کد ست: {}\n دوست شما این لینک را باز کند تا ست را دریافت کند:\n{}",
        "copy_btn": "⭐ کپی لینک",
        "channels_txt": "⌘ کانال‌های من\n─\nپست‌های حاوی کد به صورت خودکار تبدیل می‌شوند.\n\n",
        "no_channels": "◁ هنوز کانالی ثبت نکردید.",
        "add_channel_btn": "➕ افزودن کانال",
        "add_channel_prompt": "✈️ افزودن کانال\n─\nربات را در کانال خود ادمین کنید و آیدی یا یوزرنیم آن را بفرستید:\nمثل @my_channel",
        "channel_not_found": "❌ کانال پیدا نشد.",
        "channel_invalid": "⚠️ این یک کانال معتبر نیست.",
        "channel_limit_err": "⚠️ کانال باید حداقل {} عضو داشته باشد.",
        "channel_admin_err": "⚠️ ربات باید دسترسی ویرایش پیام را داشته باشد.",
        "channel_dup": "⚠️ این کانال قبلا ثبت شده است.",
        "channel_success": "✅ کانال با موفقیت ثبت شد.",
        "help_txt": "❓ راهنمای ربات\n─\n1️⃣ برای ارسال اینلاین:\n`@bot_username text [code]`\n2️⃣ ارسال لینک پک برای استخراج\n3️⃣ دکمه زیر برای ساخت پک‌های شخصی کاربرد دارد:",
        "support_txt": "💎 پشتیبانی\n─\nروش ارتباطی خود را انتخاب کنید:",
        "support_chat_btn": "👨‍💻 پیوی پشتیبانی",
        "support_ticket_btn": "🎫 ارسال تیکت جدید",
        "support_prompt": "📨 پیام خود را بنویسید تا برای پشتیبانی ارسال شود:",
        "support_sent": "✅ پیام شما برای پشتیبانی ارسال شد.",
        "ticket_prompt": "🖼 متن تیکت خود را بنویسید:",
        "ticket_sent": "✅ تیکت شما ثبت شد."
    },
    "en": {
        "welcome": "Welcome {}!\n─\nWith this bot, you can send premium emojis in any chat.\nSelect from the menu below:",
        "menu_premium": "🔮 Send Premium Emoji",
        "menu_extract": "📥 Extract Emoji Code",
        "menu_account": "👤 My Account",
        "menu_help": "📚 Help Guide",
        "menu_support": "📞 Support",
        "admin_panel": "🛠 Admin Panel",
        "back": "🔙 Back",
        "lang_select": "🌐 Please select your language / لطفا زبان خود را انتخاب کنید:",
        "invalid_set": "⚠️ Invalid or expired set code.",
        "set_added": "✅ Added {} emojis from the shared set to your account.",
        "premium_section": "✨ Send Premium Emoji\n─\nSend a new message in this chat:\n⚡ Send premium emojis or use numeric code:\n`[5792080508976373427]`",
        "inline_btn": "✨ Go Inline Mode",
        "extract_section": "📤 Extract Premium Emoji Code\n─\nSend one or multiple premium emojis to me:",
        "extract_pack_btn": "🎁 Extract from Pack Link",
        "await_pack": "🎁 Send the premium emoji pack link:\nExample: `https://t.me/addemoji/PackName`",
        "invalid_pack": "⚠️ Invalid pack link.",
        "fetching_pack": "⏳ Fetching pack details...",
        "pack_empty": "⚠️ Pack is empty or invalid.",
        "pack_success": "✅ Successfully extracted {} emojis from the pack.",
        "my_emojis_title": "⭐ Saved Emojis: {}/{}",
        "no_emojis": "You haven't saved any emojis yet.",
        "add_emoji_btn": "➕ Add New Emoji",
        "limit_reached": "⛔️ Storage limit reached.",
        "send_emoji_prompt": "✏️ Send the premium emoji or its code:",
        "send_name_prompt": "🎙 First enter a custom name for this emoji:",
        "saved_success": "«{}» Saved successfully ✅",
        "account_txt": "💠 Your Account\n─\n◁ ID: {}\n◁ Name: {}\n◁ Lang: {}\n◁ Type: {}\n📈 Saved: {}/{}",
        "stats_btn": "📊 My Stats",
        "set_btn": "🔗 Share My Set",
        "change_lang_btn": "🌐 Change Language",
        "my_stats_txt": "📊 Your Stats\n─\n⭐ Emojis: {}\n📋 Channels: {}",
        "my_set_txt": "✅ Your set is ready to share!\n─\n◁ Set Code: {}\n Your friend can open this link to get the entire set:\n{}",
        "copy_btn": "⭐ Copy Link",
        "channels_txt": "⌘ My Channels\n─\nPosts with codes will be converted automatically.\n\n",
        "no_channels": "◁ No channels registered yet.",
        "add_channel_btn": "➕ Add Channel",
        "add_channel_prompt": "✈️ Add Channel\n─\nPromote the bot to admin in your channel and send its ID or Username:\nE.g., @my_channel",
        "channel_not_found": "❌ Channel not found.",
        "channel_invalid": "⚠️ Not a valid channel.",
        "channel_limit_err": "⚠️ Channel must have at least {} members.",
        "channel_admin_err": "⚠️ Bot needs 'Edit Messages' permission.",
        "channel_dup": "⚠️ This channel is already registered.",
        "channel_success": "✅ Channel registered successfully.",
        "help_txt": "❓ Bot Help Guide\n─\n1️⃣ To send inline:\n`@bot_username text [code]`\n2️⃣ Send pack link to extract codes.\n3️⃣ Use the button below to easily build your own custom packs:",
        "support_txt": "💎 Support\n─\nChoose your communication method:",
        "support_chat_btn": "👨‍💻 Support PM",
        "support_ticket_btn": "🎫 Submit Ticket",
        "support_prompt": "📨 Write your message to send directly to support:",
        "support_sent": "✅ Message sent to support team.",
        "ticket_prompt": "🖼 Write your ticket description:",
        "ticket_sent": "✅ Ticket submitted successfully."
    }
}

def get_txt(user_id: int, key: str) -> str:
    u = get_user(user_id)
    lang = u["lang"] if u and u.get("lang") else "fa"
    return STRINGS.get(lang, STRINGS["fa"]).get(key, STRINGS["fa"][key])

# ================= ایاگرام ستاپ =================
bot = Bot(token=BOT_TOKEN, default_auth_date_format=None)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

class BotStates(StatesGroup):
    await_lang = State()
    await_pack_link = State()
    await_add_emoji_name = State()
    await_add_emoji_id = State()
    await_channel_id = State()
    await_support_msg = State()
    await_ticket_msg = State()
    admin_unlimit_target = State()
    admin_broadcast_msg = State()

# ================= کیبوردهای منوی اصلی (رنگی‌شده با استایل تصاویر) =================
def get_main_menu(user_id: int) -> InlineKeyboardMarkup:
    ensure_user(user_id)
    btn_premium = InlineKeyboardButton(text=get_txt(user_id, "menu_premium"), callback_data="menu_premium")
    btn_extract = InlineKeyboardButton(text=get_txt(user_id, "menu_extract"), callback_data="menu_extract")
    btn_account = InlineKeyboardButton(text=get_txt(user_id, "menu_account"), callback_data="menu_account")
    btn_help = InlineKeyboardButton(text=get_txt(user_id, "menu_help"), callback_data="menu_help")
    btn_support = InlineKeyboardButton(text=get_txt(user_id, "menu_support"), callback_data="menu_support")
    
    keyboard = [
        [btn_premium],
        [btn_extract],
        [btn_account, btn_help],
        [btn_support]
    ]
    if user_id in ADMIN_IDS:
        keyboard.append([InlineKeyboardButton(text=get_txt(user_id, "admin_panel"), callback_data="admin_panel")])
        
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# ================= هندلرهای بیس / استارت =================
@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext, command: CommandObject):
    user_id = message.from_user.id
    ensure_user(user_id, message.from_user.first_name, message.from_user.username)
    
    if command.args and command.args.startswith("set_"):
        code = command.args[4:]
        owner = find_user_by_set_code(code)
        if not owner:
            await message.reply(get_txt(user_id, "invalid_set"))
            return
        
        src_emojis = list_saved_emojis(owner["user_id"])
        limit = user_limit(user_id)
        added = 0
        for row in src_emojis:
            if limit is not None and user_emoji_count(user_id) >= limit:
                break
            add_saved_emoji(user_id, row["name"], row["doc_id"])
            added += 1
        await message.reply(get_txt(user_id, "set_added").format(added))
        return

    u = get_user(user_id)
    if not u or not u.get("lang"):
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="فارسی 🇮🇷", callback_data="setlang_fa"),
             InlineKeyboardButton(text="English 🇬🇧", callback_data="setlang_en")]
        ])
        await message.reply(STRINGS["fa"]["lang_select"], reply_markup=kb)
        return

    txt = get_txt(user_id, "welcome").format(message.from_user.first_name or "User")
    await message.reply(txt, reply_markup=get_main_menu(user_id))

@dp.callback_query(F.data.startswith("setlang_"))
async def callback_set_lang(callback: CallbackQuery):
    lang = callback.data.split("_")[1]
    set_user_lang(callback.from_user.id, lang)
    await callback.answer()
    txt = get_txt(callback.from_user.id, "welcome").format(callback.from_user.first_name or "User")
    await callback.message.edit_text(txt, reply_markup=get_main_menu(callback.from_user.id))

@dp.callback_query(F.data == "back_main")
async def cb_back_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    user_id = callback.from_user.id
    txt = get_txt(user_id, "welcome").format(callback.from_user.first_name or "User")
    await callback.message.edit_text(txt, reply_markup=get_main_menu(user_id))

# ================= بخش ارسال ایموجی پرمیوم (اینلاین) =================
@dp.callback_query(F.data == "menu_premium")
async def cb_menu_premium(callback: CallbackQuery):
    user_id = callback.from_user.id
    txt = get_txt(user_id, "premium_section")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✨ " + get_txt(user_id, "inline_btn"), switch_inline_query="")],
        [InlineKeyboardButton(text=get_txt(user_id, "back"), callback_data="back_main")]
    ])
    await callback.message.edit_text(txt, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

@dp.inline_query()
async def inline_query_handler(inline_query: InlineQuery):
    query = inline_query.query.strip()
    if not query:
        await inline_query.answer(results=[
            InlineQueryResultArticle(
                id="1",
                title="✨ Send Premium Emoji",
                description="Type: Hello [emoji_id]",
                input_message_content=InputTextMessageContent(
                    message_text=f"Example: Hello [5350291836378307462]"
                )
            )
        ], cache_time=0, is_personal=True)
        return

    matches = list(CODE_RE.finditer(query))
    if not matches:
        await inline_query.answer(results=[
            InlineQueryResultArticle(
                id="2",
                title="⚠️ Wrong Format",
                description="Usage: text [emoji_id]",
                input_message_content=InputTextMessageContent(message_text="Usage: text [emoji_id]")
            )
        ], cache_time=0, is_personal=True)
        return

    text_buffer = ""
    entities = []
    last_idx = 0
    
    for m in matches:
        text_buffer += query[last_idx:m.start()]
        entities.append(MessageEntity(
            type="custom_emoji",
            offset=len(text_buffer.encode("utf-16-le")) // 2,
            length=1,
            custom_emoji_id=m.group(1)
        ))
        text_buffer += FALLBACK_EMOJI
        last_idx = m.end()
        
    text_buffer += query[last_idx:]

    await inline_query.answer(results=[
        InlineQueryResultArticle(
            id="3",
            title=f"Send with {len(matches)} Premium Emojis ✨",
            description=text_buffer[:50],
            input_message_content=InputTextMessageContent(
                message_text=text_buffer,
                entities=entities
            )
        )
    ], cache_time=0, is_personal=True)

# ================= بخش استخراج کدهای ایموجی (با رفع باگ نمایش زنده لیست) =================
@dp.callback_query(F.data == "menu_extract")
async def cb_menu_extract(callback: CallbackQuery):
    user_id = callback.from_user.id
    txt = get_txt(user_id, "extract_section")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 " + get_txt(user_id, "extract_pack_btn"), callback_data="extract_pack")],
        [InlineKeyboardButton(text=get_txt(user_id, "back"), callback_data="back_main")]
    ])
    await callback.message.edit_text(txt, reply_markup=kb)

@dp.callback_query(F.data == "extract_pack")
async def cb_extract_pack(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    await state.set_state(BotStates.await_pack_link)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_txt(user_id, "back"), callback_data="menu_extract")]
    ])
    await callback.message.edit_text(get_txt(user_id, "await_pack"), reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

@dp.message(BotStates.await_pack_link)
async def process_pack_link(message: Message, state: FSMContext):
    user_id = message.from_user.id
    match = PACK_LINK_RE.search(message.text or "")
    if not match:
        await message.reply(get_txt(user_id, "invalid_pack"))
        return
        
    await state.clear()
    status_msg = await message.reply(get_txt(user_id, "fetching_pack"))
    short_name = match.group(1)
    
    try:
        stickerset = await bot.get_sticker_set(name=short_name)
        if not stickerset or not stickerset.stickers:
            await status_msg.edit_text(get_txt(user_id, "pack_empty"))
            return
            
        # ساخت بخش هدر متن
        output_txt = f"📦 Pack: `{short_name}`\n─\n"
        entities = []
        
        # استخراج تک‌تک ایموجی‌ها به همراه آیدی اختصاصی خودشان
        for idx, sticker in enumerate(stickerset.stickers[:35], 1): 
            if not sticker.custom_emoji_id:
                continue
                
            # محاسبه آفست کاراکتر بر اساس انکودینگ UTF-16 که تلگرام برای متون نیاز دارد
            current_offset = len(output_txt.encode("utf-16-le")) // 2
            
            # اضافه کردن سطر جدید (ابتدا ستاره به عنوان جایگاه موقت رندر، سپس کد عددی)
            output_txt += f"{idx}. {FALLBACK_EMOJI}  `[{sticker.custom_emoji_id}]`\n"
            
            # آدرس‌دهی دقیق به تلگرام برای جایگزین کردن ستاره با ایموجی پرمیوم اصلی خودش
            emoji_offset = current_offset + len(f"{idx}. ".encode("utf-16-le")) // 2
            
            entities.append(MessageEntity(
                type="custom_emoji",
                offset=emoji_offset,
                length=1,
                custom_emoji_id=str(sticker.custom_emoji_id) # آیدی اختصاصی همین ایموجی
            ))
            
        await message.reply(
    output_txt,
    entities=entities
)
        await status_msg.edit_text(get_txt(user_id, "pack_success").format(len(stickerset.stickers)))
        
    except Exception as e:
        await status_msg.edit_text(f"❌ Error: {str(e)}")

@dp.message(F.chat.type == "private", F.custom_emoji_text)
async def process_direct_emoji(message: Message):
    custom_emoji_ids = [e.custom_emoji_id for e in message.entities if e.type == "custom_emoji"]
    if custom_emoji_ids:
        res = "🅰 Premium Emojis Detected:\n\n"
        entities = []
        for cid in custom_emoji_ids:
            current_offset = len(res.encode("utf-16-le")) // 2
            res += f"{FALLBACK_EMOJI} Code: `{cid}`\n"
            entities.append(MessageEntity(
                type="custom_emoji",
                offset=current_offset,
                length=1,
                custom_emoji_id=str(cid)
            ))
        await message.reply(res, entities=entities)

# ================= مدیریت ذخیره شخصی (ایموجی‌های من) =================
PAGE_SIZE = 5

def render_my_emojis(user_id: int, page: int = 0) -> tuple:
    rows = list_saved_emojis(user_id)
    total = len(rows)
    limit = user_limit(user_id)
    limit_txt = "Unlimited" if limit is None else str(limit)
    
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(0, min(page, total_pages - 1))
    page_rows = rows[page * PAGE_SIZE : (page + 1) * PAGE_SIZE]
    
    text = get_txt(user_id, "my_emojis_title").format(total, limit_txt) + "\n"
    kb_builder = []
    entities = []
    
    for r in page_rows:
        current_offset = len(text.encode("utf-16-le")) // 2
        text += f"▪️ {r['name']}: {FALLBACK_EMOJI}\n"
        
        entities.append(MessageEntity(
            type="custom_emoji",
            offset=current_offset + len(f"▪️ {r['name']}: ".encode("utf-16-le")) // 2,
            length=1,
            custom_emoji_id=str(r['doc_id'])
        ))
        
        kb_builder.append([
            InlineKeyboardButton(text=f"🧬 {r['name']}", callback_data="noop"), 
            InlineKeyboardButton(text="🗑", callback_data=f"del_{r['id']}_{page}") 
        ])
        
    nav_row = [
        InlineKeyboardButton(text=f"◀️", callback_data=f"page_{page-1}"),
        InlineKeyboardButton(text=f"{page+1}/{total_pages}", callback_data="noop"),
        InlineKeyboardButton(text="➡️", callback_data=f"page_{page+1}")
    ]
    kb_builder.append(nav_row)
    kb_builder.append([InlineKeyboardButton(text=get_txt(user_id, "add_emoji_btn"), callback_data="add_emo")])
    kb_builder.append([InlineKeyboardButton(text=get_txt(user_id, "back"), callback_data="menu_account")])
    
    return text, InlineKeyboardMarkup(inline_keyboard=kb_builder), entities

@dp.callback_query(F.data == "menu_my_emojis")
async def cb_my_emojis(callback: CallbackQuery):
    user_id = callback.from_user.id
    txt, kb, entities = render_my_emojis(user_id, 0)
    await callback.message.edit_text(text=txt, reply_markup=kb, entities=entities)

@dp.callback_query(F.data.startswith("page_"))
async def cb_my_emojis_page(callback: CallbackQuery):
    user_id = callback.from_user.id
    page = int(callback.data.split("_")[1])
    txt, kb, entities = render_my_emojis(user_id, page)
    try:
        await callback.message.edit_text(text=txt, reply_markup=kb, entities=entities)
    except TelegramBadRequest:
        await callback.answer()

@dp.callback_query(F.data.startswith("del_"))
async def cb_del_emoji(callback: CallbackQuery):
    user_id = callback.from_user.id
    parts = callback.data.split("_")
    row_id = int(parts[1])
    page = int(parts[2])
    
    delete_saved_emoji(row_id, user_id)
    await callback.answer("🗑 Deleted")
    txt, kb, entities = render_my_emojis(user_id, page)
    await callback.message.edit_text(text=txt, reply_markup=kb, entities=entities)

@dp.callback_query(F.data == "noop")
async def cb_noop(callback: CallbackQuery):
    await callback.answer()

# ---- فیکس باگ بخش افزودن ایموجی ----
@dp.callback_query(F.data == "add_emo")
async def cb_add_emo_start(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    limit = user_limit(user_id)
    if limit is not None and user_emoji_count(user_id) >= limit:
        await callback.answer(get_txt(user_id, "limit_reached"), show_alert=True)
        return
        
    await state.set_state(BotStates.await_add_emoji_name) 
    await callback.message.edit_text(get_txt(user_id, "send_name_prompt"))

@dp.message(BotStates.await_add_emoji_name)
async def process_emoji_name(message: Message, state: FSMContext):
    name = (message.text or "").strip()
    if not name:
        await message.reply("❌ نام نامعتبر است. مجددا ارسال کنید:")
        return
    await state.update_data(saved_name=name)
    await state.set_state(BotStates.await_add_emoji_id)
    await message.reply(get_txt(message.from_user.id, "send_emoji_prompt"))

@dp.message(BotStates.await_add_emoji_id)
async def process_emoji_id_save(message: Message, state: FSMContext):
    user_id = message.from_user.id
    data = await state.get_data()
    name = data.get("saved_name", "Emoji")
    
    custom_emoji_ids = [e.custom_emoji_id for e in message.entities if e.type == "custom_emoji"] if message.entities else []
    if not custom_emoji_ids:
        matches = CODE_RE.findall(message.text or "")
        if matches:
            custom_emoji_ids = [matches[0]]
            
    if not custom_emoji_ids:
        await message.reply("⚠️ هیچ کدی یا ایموجی پرمیومی یافت نشد. مجددا ارسال کنید:")
        return
        
    doc_id = custom_emoji_ids[0]
    await state.clear()
    
    add_saved_emoji(user_id, name, doc_id)
    
    success_text = get_txt(user_id, "saved_success").format(name)
    full_text = f"{FALLBACK_EMOJI} {success_text}"
    ent = MessageEntity(type="custom_emoji", offset=0, length=1, custom_emoji_id=str(doc_id))
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ نمایش ایموجی‌ها", callback_data="menu_my_emojis")]
    ])
    await message.reply(text=full_text, entities=[ent], reply_markup=kb)

# ================= حساب کاربری من =================
@dp.callback_query(F.data == "menu_account")
async def cb_menu_account(callback: CallbackQuery):
    user_id = callback.from_user.id
    u = get_user(user_id)
    limit = user_limit(user_id)
    limit_txt = "Unlimited" if limit is None else str(limit)
    count = user_emoji_count(user_id)
    kind = "Premium (Unlimited)" if u.get("unlimited") else "Regular User"
    
    txt = get_txt(user_id, "account_txt").format(
        user_id, callback.from_user.first_name or "-", u.get("lang", "fa"), kind, count, limit_txt
    )
    
    # منوی شیک حساب کاربری بر اساس عکس‌ها
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ ایموجی‌های من", callback_data="menu_my_emojis"),
         InlineKeyboardButton(text=get_txt(user_id, "stats_btn"), callback_data="my_stats")],
        [InlineKeyboardButton(text="📢 کانال‌های من", callback_data="menu_channels"),
         InlineKeyboardButton(text=get_txt(user_id, "set_btn"), callback_data="my_set")],
        [InlineKeyboardButton(text=get_txt(user_id, "change_lang_btn"), callback_data="change_lang")],
        [InlineKeyboardButton(text=get_txt(user_id, "back"), callback_data="back_main")]
    ])
    await callback.message.edit_text(txt, reply_markup=kb)

@dp.callback_query(F.data == "change_lang")
async def cb_change_lang_panel(callback: CallbackQuery):
    user_id = callback.from_user.id
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="فارسی 🇮🇷", callback_data="setlang_fa"),
         InlineKeyboardButton(text="English 🇬🇧", callback_data="setlang_en")],
        [InlineKeyboardButton(text=get_txt(user_id, "back"), callback_data="menu_account")]
    ])
    await callback.message.edit_text(STRINGS[get_user(user_id)["lang"]]["lang_select"], reply_markup=kb)

@dp.callback_query(F.data == "my_stats")
async def cb_my_stats(callback: CallbackQuery):
    user_id = callback.from_user.id
    count = user_emoji_count(user_id)
    channels_count = len(list_channels(user_id))
    txt = get_txt(user_id, "my_stats_txt").format(count, channels_count)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_txt(user_id, "back"), callback_data="menu_account")]
    ])
    await callback.message.edit_text(txt, reply_markup=kb)

@dp.callback_query(F.data == "my_set")
async def cb_my_set(callback: CallbackQuery):
    user_id = callback.from_user.id
    code = get_or_create_set_code(user_id)
    bot_user = await bot.get_me()
    link = f"https://t.me/{bot_user.username}?start=set_{code}"
    
    txt = get_txt(user_id, "my_set_txt").format(code, link)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_txt(user_id, "copy_btn"), callback_data=f"copy_{code}")],
        [InlineKeyboardButton(text=get_txt(user_id, "back"), callback_data="menu_account")]
    ])
    await callback.message.edit_text(txt, reply_markup=kb)

@dp.callback_query(F.data.startswith("copy_"))
async def cb_copy_link(callback: CallbackQuery):
    code = callback.data.split("_")[1]
    bot_user = await bot.get_me()
    link = f"https://t.me/{bot_user.username}?start=set_{code}"
    await callback.answer(f"Link: {link}", show_alert=True)

# ================= مدیریت کانال‌ها =================
@dp.callback_query(F.data == "menu_channels")
async def cb_menu_channels(callback: CallbackQuery):
    user_id = callback.from_user.id
    chans = list_channels(user_id)
    txt = get_txt(user_id, "channels_txt")
    
    if not chans:
        txt += get_txt(user_id, "no_channels")
    else:
        txt += "\n".join(f"◁ {c['title'] or c['channel_id']}" for c in chans)
        
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_txt(user_id, "add_channel_btn"), callback_data="add_channel_start")],
        [InlineKeyboardButton(text=get_txt(user_id, "back"), callback_data="menu_account")]
    ])
    await callback.message.edit_text(txt, reply_markup=kb)

@dp.callback_query(F.data == "add_channel_start")
async def cb_add_channel_start(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    await state.set_state(BotStates.await_channel_id)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_txt(user_id, "back"), callback_data="menu_channels")]
    ])
    await callback.message.edit_text(get_txt(user_id, "add_channel_prompt"), reply_markup=kb)

@dp.message(BotStates.await_channel_id)
async def process_channel_input(message: Message, state: FSMContext):
    user_id = message.from_user.id
    raw = (message.text or "").strip()
    await state.clear()
    
    try:
        chat = await bot.get_chat(raw)
    except Exception:
        await message.reply(get_txt(user_id, "channel_not_found"))
        return
        
    if chat.type != "channel":
        await message.reply(get_txt(user_id, "channel_invalid"))
        return
        
    try:
        members = await bot.get_chat_member_count(chat.id)
    except Exception:
        members = 0
        
    if members < CHANNEL_MIN_MEMBERS:
        await message.reply(get_txt(user_id, "channel_limit_err").format(CHANNEL_MIN_MEMBERS))
        return
        
    try:
        member = await chat.get_member(user_id=(await bot.get_me()).id)
        if not member.can_edit_messages:
            await message.reply(get_txt(user_id, "channel_admin_err"))
            return
    except Exception:
        await message.reply(get_txt(user_id, "channel_admin_err"))
        return
        
    ok = add_channel(user_id, chat.id, chat.title)
    if not ok:
        await message.reply(get_txt(user_id, "channel_dup"))
        return
        
    await message.reply(get_txt(user_id, "channel_success"))

@dp.channel_post(F.text)
async def auto_convert_channel_post(message: Message):
    if not is_registered_channel(message.chat.id):
        return
        
    matches = list(CODE_RE.finditer(message.text))
    if not matches:
        return
        
    text_buffer = ""
    entities = []
    last_idx = 0
    
    for m in matches:
        text_buffer += message.text[last_idx:m.start()]
        entities.append(MessageEntity(
            type="custom_emoji",
            offset=len(text_buffer.encode("utf-16-le")) // 2,
            length=1,
            custom_emoji_id=str(m.group(1)) 
        ))
        text_buffer += FALLBACK_EMOJI
        last_idx = m.end()
        
    text_buffer += message.text[last_idx:]
    
    try:
        await bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=message.message_id,
            text=text_buffer,
            entities=entities
        )
    except Exception as e:
        print(f"Channel replace log err: {e}")

# ================= بخش راهنما =================
@dp.callback_query(F.data == "menu_help")
async def cb_menu_help(callback: CallbackQuery):
    user_id = callback.from_user.id
    txt = get_txt(user_id, "help_txt")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛠️ Maker Bot: @TgEmojis_bot", url="https://t.me/TgEmojis_bot")],
        [InlineKeyboardButton(text=get_txt(user_id, "back"), callback_data="back_main")]
    ])
    await callback.message.edit_text(txt, reply_markup=kb)

# ================= بخش پشتیبانی و تیکت‌ها =================
@dp.callback_query(F.data == "menu_support")
async def cb_menu_support(callback: CallbackQuery):
    user_id = callback.from_user.id
    txt = get_txt(user_id, "support_txt")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_txt(user_id, "support_chat_btn"), callback_data="support_chat"),
         InlineKeyboardButton(text=get_txt(user_id, "support_ticket_btn"), callback_data="support_ticket")],
        [InlineKeyboardButton(text=get_txt(user_id, "back"), callback_data="back_main")]
    ])
    await callback.message.edit_text(txt, reply_markup=kb)

@dp.callback_query(F.data == "support_chat")
async def cb_support_chat(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    await state.set_state(BotStates.await_support_msg)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_txt(user_id, "back"), callback_data="menu_support")]
    ])
    await callback.message.edit_text(get_txt(user_id, "support_prompt"), reply_markup=kb)

@dp.message(BotStates.await_support_msg)
async def process_support_msg(message: Message, state: FSMContext):
    user_id = message.from_user.id
    await state.clear()
    
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"✉️ New PM Support\nFrom: {message.from_user.first_name} (@{message.from_user.username or '-'}) | ID: `{user_id}`\n\n{message.text}\n\nUse command `/reply {user_id} text` to answer."
            )
        except Exception:
            pass
    await message.reply(get_txt(user_id, "support_sent"))

@dp.message(Command("reply"))
async def cmd_admin_reply(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.reply("Usage: /reply target_id text")
        return
    target_id = int(parts[1])
    reply_text = parts[2]
    
    try:
        await bot.send_message(target_id, f"💎 Support Reply:\n\n{reply_text}")
        await message.reply("✅ Sent.")
    except Exception as e:
        await message.reply(f"❌ Failed: {e}")

@dp.callback_query(F.data == "support_ticket")
async def cb_support_ticket(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    await state.set_state(BotStates.await_ticket_msg)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_txt(user_id, "back"), callback_data="menu_support")]
    ])
    await callback.message.edit_text(get_txt(user_id, "ticket_prompt"), reply_markup=kb)

@dp.message(BotStates.await_ticket_msg)
async def process_ticket_msg(message: Message, state: FSMContext):
    user_id = message.from_user.id
    await state.clear()
    add_ticket(user_id, message.text or "")
    
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"🎫 Ticket New!\nFrom: {message.from_user.first_name} | ID: `{user_id}`\n\n{message.text}"
            )
        except Exception:
            pass
    await message.reply(get_txt(user_id, "ticket_sent"))

# ================= پنل مدیریت ادمین =================
@dp.callback_query(F.data == "admin_panel")
async def cb_admin_panel(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Stats Detailed", callback_data="admin_stats")],
        [InlineKeyboardButton(text="🔓 Unlimit User", callback_data="admin_unlimit")],
        [InlineKeyboardButton(text="📢 Broadcast MSG", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="🔙 Back", callback_data="back_main")]
    ])
    await callback.message.edit_text("⚙️ Admin Management Panel", reply_markup=kb)

@dp.callback_query(F.data == "admin_stats")
async def cb_admin_stats(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        return
    s = db_stats()
    txt = f"📊 System Details:\n\nUsers: {s['users']}\nSaved Emojis: {s['emojis']}\nChannels: {s['channels']}\nOpen Tickets: {s['open_tickets']}\nPremium Users: {s['unlimited_users']}"
    kb = InlineKeyboardMarkup(inline_keyboard=[[[InlineKeyboardButton(text="Back", callback_data="admin_panel")]]])
    await callback.message.edit_text(txt, reply_markup=kb)

@dp.callback_query(F.data == "admin_unlimit")
async def cb_admin_unlimit(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        return
    await state.set_state(BotStates.admin_unlimit_target)
    await callback.message.edit_text("Enter user numeric ID to lift storage boundaries:")

@dp.message(BotStates.admin_unlimit_target)
async def process_admin_unlimit(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    raw = (message.text or "").strip()
    await state.clear()
    if not raw.isdigit():
        await message.reply("Invalid numeric id.")
        return
    target_id = int(raw)
    ensure_user(target_id)
    
    cur = _conn.cursor()
    cur.execute("UPDATE users SET unlimited=1 WHERE user_id=?", (target_id,))
    _conn.commit()
    await message.reply(f"User {target_id} is now unrestricted Premium member.")
    try:
        await bot.send_message(target_id, "🎉 Your emoji storage limits have been removed by administrator!")
    except Exception:
        pass

@dp.callback_query(F.data == "admin_broadcast")
async def cb_admin_broadcast(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        return
    await state.set_state(BotStates.admin_broadcast_msg)
    await callback.message.edit_text("Send message text to broadcast to everyone:")

@dp.message(BotStates.admin_broadcast_msg)
async def process_admin_broadcast(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    await state.clear()
    ids = all_user_ids()
    status_msg = await message.reply(f"⏳ Broadcasting to {len(ids)} users...")
    
    success, fail = 0, 0
    for uid in ids:
        try:
            await bot.send_message(uid, f"📢 Broadcast:\n\n{message.text}")
            success += 1
        except Exception:
            fail += 1
            
    await status_msg.edit_text(f"✅ Broadcast Done.\nSuccess: {success} | Failed: {fail}")


# ================= استارت نهایی سرور ایاگرام =================
if __name__ == "__main__":
    import asyncio
    print("Aiogram Bot service successfully initiated...")
    asyncio.run(dp.start_polling(bot))
