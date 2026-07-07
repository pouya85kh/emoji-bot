import os
import re
import json
import sqlite3
import asyncio
import random
import string
import datetime
from telethon import TelegramClient, events, Button
from telethon.tl import types, functions
from telethon.tl.types import UpdateBotInlineSend
from telethon.errors import UserIsBlockedError, ChatWriteForbiddenError
 
# ================= تنظیمات =================
API_ID    = int(os.environ["API_ID"])
API_HASH  = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]
 
ADMIN_IDS = {7049497099}          # آیدی عددی ادمین‌ها
SUPPORT_USERNAME = "nooooofear"   # فقط جهت نمایش/رفرنس - دیگر پیوی مستقیم داده نمی‌شود
 
FALLBACK = "\u2b50"
 
DEFAULT_EMOJI_LIMIT = 50
CHANNEL_MIN_MEMBERS = 50
PACK_LINK_RE = re.compile(r"(?:addemoji|addstickers)/([a-zA-Z0-9_]+)")
CODE_RE = re.compile(r"\[(\d+)\]")
 
# مسیر دیتابیس - روی ریلوی حتما یک Volume به این مسیر وصل کن تا دیتا پاک نشود
DB_PATH = os.environ.get("DB_PATH", "bot.db")
 
# =============================================================
# آیدی عددی ایموجی‌های پرمیوم استفاده‌شده در متن‌های ربات.
# !! این‌ها placeholder هستند (فعلا با DECO_EMOJI_ID پر شده‌اند) !!
# حتما هرکدام را با آیدی واقعی ایموجی پرمیومی که مالک/دارای دسترسی به آن هستی جایگزین کن،
# وگرنه ارسال آن پیام با خطا مواجه می‌شود.
# =============================================================
DECO_EMOJI_ID = 5057918405923832965
 
EMOJI = {
    "rocket":      DECO_EMOJI_ID,  # 📈 خوش‌آمد / حساب کاربری
    "telegram":    DECO_EMOJI_ID,  # ✈️ سرتیترهای مرتبط با پک/کانال
    "star":        DECO_EMOJI_ID,  # ⭐ ایموجی پریمیوم / ست
    "link":        DECO_EMOJI_ID,  # 🔗 استخراج کد ایموجی
    "panel":       DECO_EMOJI_ID,  # 🖥 حساب من
    "help":        DECO_EMOJI_ID,  # ❓ راهنما
    "mail":        5971889748615105853,  # ✉️ پشتیبانی
    "gem":         DECO_EMOJI_ID,  # 💎 پشتیبانی هدر
    "bolt":        DECO_EMOJI_ID,  # ⚡ نکات/دسترسی‌ها
    "note":        DECO_EMOJI_ID,  # 📝 توضیحات
    "mic":         DECO_EMOJI_ID,  # 🎙 نکات فرعی
    "gift":        DECO_EMOJI_ID,  # 🎁 استخراج از لینک پک
    "chart":       DECO_EMOJI_ID,  # 📊 آمار
    "folder":      DECO_EMOJI_ID,  # 📋 کانال‌های من
    "check":       DECO_EMOJI_ID,  # ✅ تایید / ست آماده شد
    "gear":        DECO_EMOJI_ID,  # ⌘ کانال‌های من هدر
    "pencil":      DECO_EMOJI_ID,  # ✏️ افزودن کانال / ایموجی
    "dino":        DECO_EMOJI_ID,  # 🦖 پیوی پشتیبانی
    "ticket":      DECO_EMOJI_ID,  # 🖼 ارسال تیکت
    "back":        DECO_EMOJI_ID,  # 🔙 بازگشت / لغو / حذف
}
 
SESSION_PATH = os.environ.get("SESSION_PATH", "/data/bot")

client = TelegramClient(
    SESSION_PATH,
    API_ID,
    API_HASH
).start(bot_token=BOT_TOKEN)
 
# حافظه موقت برای مراحل چندپیامی (state هر کاربر)
pending = {}   # user_id -> dict(action=..., **extra)
 
# =================================================================================
# دیتابیس
# =================================================================================
_db_lock = asyncio.Lock()
_conn = sqlite3.connect(DB_PATH, check_same_thread=False)
_conn.row_factory = sqlite3.Row
 
 
def db_init():
    cur = _conn.cursor()
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS users(
        user_id INTEGER PRIMARY KEY,
        first_name TEXT,
        username TEXT,
        emoji_limit INTEGER DEFAULT 50,
        unlimited INTEGER DEFAULT 0,
        set_code TEXT,
        joined_at TEXT
    );
    CREATE TABLE IF NOT EXISTS saved_emojis(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        name TEXT,
        doc_id INTEGER,
        alt TEXT
    );
    CREATE TABLE IF NOT EXISTS channels(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        channel_id TEXT,
        title TEXT
    );
    CREATE TABLE IF NOT EXISTS tickets(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        message TEXT,
        status TEXT DEFAULT 'open',
        created_at TEXT
    );
    """)
    _conn.commit()
    # مهاجرت برای دیتابیس‌های قدیمی‌تری که هنوز ستون alt را ندارند
    try:
        cur.execute("ALTER TABLE saved_emojis ADD COLUMN alt TEXT")
        _conn.commit()
    except sqlite3.OperationalError:
        pass


db_init()
 
 
def ensure_user(user_id, first_name=None, username=None):
    cur = _conn.cursor()
    cur.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    if row is None:
        cur.execute(
            "INSERT INTO users(user_id, first_name, username, emoji_limit, unlimited, joined_at) VALUES(?,?,?,?,?,?)",
            (user_id, first_name, username, DEFAULT_EMOJI_LIMIT, 0, datetime.datetime.utcnow().isoformat()),
        )
        _conn.commit()
    else:
        cur.execute("UPDATE users SET first_name=?, username=? WHERE user_id=?", (first_name, username, user_id))
        _conn.commit()
 
 
def get_user(user_id):
    cur = _conn.cursor()
    cur.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    return cur.fetchone()
 
 
def user_emoji_count(user_id):
    cur = _conn.cursor()
    cur.execute("SELECT COUNT(*) c FROM saved_emojis WHERE user_id=?", (user_id,))
    return cur.fetchone()["c"]
 
 
def user_limit(user_id):
    u = get_user(user_id)
    if u is None:
        return DEFAULT_EMOJI_LIMIT
    if u["unlimited"]:
        return None  # نامحدود
    return u["emoji_limit"]
 
 
def add_saved_emoji(user_id, name, doc_id, alt=None):
    cur = _conn.cursor()
    cur.execute("INSERT INTO saved_emojis(user_id, name, doc_id, alt) VALUES(?,?,?,?)", (user_id, name, doc_id, alt))
    _conn.commit()
 
 
def list_saved_emojis(user_id):
    cur = _conn.cursor()
    cur.execute("SELECT * FROM saved_emojis WHERE user_id=? ORDER BY id", (user_id,))
    return cur.fetchall()
 
 
def delete_saved_emoji(row_id, user_id):
    cur = _conn.cursor()
    cur.execute("DELETE FROM saved_emojis WHERE id=? AND user_id=?", (row_id, user_id))
    _conn.commit()
 
 
def get_or_create_set_code(user_id):
    u = get_user(user_id)
    if u and u["set_code"]:
        return u["set_code"]
    code = "".join(random.choices(string.ascii_uppercase + string.digits, k=7))
    cur = _conn.cursor()
    cur.execute("UPDATE users SET set_code=? WHERE user_id=?", (code, user_id))
    _conn.commit()
    return code
 
 
def find_user_by_set_code(code):
    cur = _conn.cursor()
    cur.execute("SELECT * FROM users WHERE set_code=?", (code,))
    return cur.fetchone()
 
 
def add_channel(user_id, channel_id, title):
    cur = _conn.cursor()
    cur.execute("SELECT id FROM channels WHERE channel_id=?", (str(channel_id),))
    if cur.fetchone():
        return False
    cur.execute("INSERT INTO channels(user_id, channel_id, title) VALUES(?,?,?)", (user_id, str(channel_id), title))
    _conn.commit()
    return True
 
 
def list_channels(user_id):
    cur = _conn.cursor()
    cur.execute("SELECT * FROM channels WHERE user_id=?", (user_id,))
    return cur.fetchall()
 
 
def is_registered_channel(channel_id):
    cur = _conn.cursor()
    cur.execute("SELECT * FROM channels WHERE channel_id=?", (str(channel_id),))
    return cur.fetchone()
 
 
def add_ticket(user_id, message):
    cur = _conn.cursor()
    cur.execute(
        "INSERT INTO tickets(user_id, message, status, created_at) VALUES(?,?,?,?)",
        (user_id, message, "open", datetime.datetime.utcnow().isoformat()),
    )
    _conn.commit()
 
 
def stats():
    cur = _conn.cursor()
    cur.execute("SELECT COUNT(*) c FROM users")
    users_count = cur.fetchone()["c"]
    cur.execute("SELECT COUNT(*) c FROM saved_emojis")
    emojis_count = cur.fetchone()["c"]
    cur.execute("SELECT COUNT(*) c FROM channels")
    channels_count = cur.fetchone()["c"]
    cur.execute("SELECT COUNT(*) c FROM tickets WHERE status='open'")
    open_tickets = cur.fetchone()["c"]
    cur.execute("SELECT COUNT(*) c FROM users WHERE unlimited=1")
    unlimited_users = cur.fetchone()["c"]
    return {
        "users": users_count,
        "emojis": emojis_count,
        "channels": channels_count,
        "open_tickets": open_tickets,
        "unlimited_users": unlimited_users,
    }
 
 
def all_user_ids():
    cur = _conn.cursor()
    cur.execute("SELECT user_id FROM users")
    return [r["user_id"] for r in cur.fetchall()]
 
 
# =================================================================================
# ابزارهای عمومی
# =================================================================================
def utf16_len(text: str) -> int:
    return len(text.encode("utf-16-le")) // 2
 
 
def emo(key: str, length: int = 1):
    """یک MessageEntityCustomEmoji برای درج در ابتدای متن با آفست مشخص می‌سازد."""
    return types.MessageEntityCustomEmoji(offset=0, length=length, document_id=EMOJI[key])
 
 
def with_deco(key: str, text: str):
    """متن را با یک ایموجی پرمیوم در ابتدا و یک اینتیتی مربوطه برمی‌گرداند."""
    full_text = FALLBACK + "  " + text
    ent = types.MessageEntityCustomEmoji(offset=0, length=1, document_id=EMOJI[key])
    return full_text, [ent]
 
 
def doc_alt(doc) -> str:
    for attr in doc.attributes:
        if isinstance(attr, types.DocumentAttributeCustomEmoji):
            return attr.alt or FALLBACK
    return FALLBACK
 
 
def extract_entities_from_message(event):
    """آیدی ایموجی‌های پرمیوم موجود در خودِ پیام (اگر کاربر ایموجی واقعی فرستاده باشد) را برمی‌گرداند."""
    ids = []
    if event.message and event.message.entities:
        for e in event.message.entities:
            if isinstance(e, types.MessageEntityCustomEmoji):
                ids.append(e.document_id)
    return ids
 
 
def parse_codes_from_text(text):
    return [int(m.group(1)) for m in CODE_RE.finditer(text)]


def extract_emojis_with_alt(event):
    """
    برخلاف extract_entities_from_message، این تابع برای هر ایموجی پرمیومی که کاربر واقعاً
    در پیام فرستاده، هم document_id و هم گلیف واقعی (alt) را برمی‌گرداند. گلیف واقعی همان
    کاراکتری‌ست که زیر entity قرار دارد و توسط کلاینت‌های بدون رندر (یا در حالت fallback) نشان
    داده می‌شود؛ بدون این، هر ایموجی هنگام ذخیره یا نمایش با یک ستاره‌ی یکسان جایگزین می‌شود.
    """
    result = []
    if event.message and event.message.entities and event.raw_text:
        text16 = event.raw_text.encode("utf-16-le")
        for e in event.message.entities:
            if isinstance(e, types.MessageEntityCustomEmoji):
                start = e.offset * 2
                end = start + e.length * 2
                try:
                    alt = text16[start:end].decode("utf-16-le")
                except Exception:
                    alt = FALLBACK
                result.append((e.document_id, alt or FALLBACK))
    return result


# =================================================================================
# جایگزینی خودکار ایموجی‌های معمولی متن با ایموجی‌های پرمیوم متناظر
# توجه مهم: این تابع فقط برای متنِ پیام‌ها کار می‌کند. تلگرام به دکمه‌های inline
# اجازه‌ی حمل هیچ entity‌ای (نه ایموجی پرمیوم و نه رنگ) را نمی‌دهد، بنابراین برچسبِ
# دکمه‌ها همیشه باید همان کاراکترهای یونیکد ساده باقی بمانند.
# =================================================================================
UNICODE_EMOJI_MAP = {
    "🚀": "rocket", "✈️": "telegram", "⭐": "star", "🔗": "link", "🖥": "panel",
    "❓": "help", "✉️": "mail", "💎": "gem", "⚡": "bolt", "📝": "note",
    "🎙": "mic", "🎁": "gift", "📊": "chart", "📋": "folder", "✅": "check",
    "⌘": "gear", "✏️": "pencil", "🦖": "dino", "🖼": "ticket", "🔙": "back",
    "📈": "rocket", "📨": "mail", "🔷": "bolt", "🎉": "gift", "📤": "link",
    "🅰": "note", "🔓": "check", "📢": "mail", "⏳": "bolt",
}


def premiumize(text: str):
    """
    هر ایموجی معمولی شناخته‌شده در متن را نگه می‌دارد ولی یک MessageEntityCustomEmoji
    متناظر رویش می‌گذارد تا در کلاینت به‌صورت ایموجی پرمیوم رندر شود.
    خروجی: (متن بدون تغییر ظاهری، لیست entityها)
    """
    entities = []
    out = ""
    i = 0
    n = len(text)
    while i < n:
        matched = False
        for ch, key in UNICODE_EMOJI_MAP.items():
            if text.startswith(ch, i):
                offset = utf16_len(out)
                out += ch
                entities.append(types.MessageEntityCustomEmoji(
                    offset=offset, length=utf16_len(ch), document_id=EMOJI[key],
                ))
                i += len(ch)
                matched = True
                break
        if not matched:
            out += text[i]
            i += 1
    return out, entities
 
 
async def edit_deco(event, text, buttons):
    """میانبر برای ویرایش پیام‌ای که تمام ایموجی‌های معمولی شناخته‌شده‌ی متنش
    باید به ایموجی پرمیوم تبدیل شوند (دکمه‌ها همچنان یونیکد ساده باقی می‌مانند)."""
    text2, ent = premiumize(text)
    await event.edit(text2, formatting_entities=ent, buttons=buttons, parse_mode=None)
 
 
async def safe_send(user_id, *args, **kwargs):
    try:
        await client.send_message(user_id, *args, **kwargs)
        return True
    except (UserIsBlockedError, ChatWriteForbiddenError):
        return False
    except Exception as e:
        print(f"send to {user_id} failed: {e}")
        return False
 
 
# =================================================================================
# منوها (کیبوردها)
# توجه: تلگرام رنگ اختصاصی هر دکمه‌ی inline را پشتیبانی نمی‌کند، همه‌ی دکمه‌ها
# با تم پیش‌فرض کلاینت کاربر نمایش داده می‌شوند و از این نظر محدودیتی در بات نیست.
# =================================================================================
def main_menu_buttons(user_id):
    rows = [
        [Button.inline("⭐ ایموجی پریمیوم", b"menu_premium"), Button.inline("🔗 استخراج کد ایموجی", b"menu_extract")],
        [Button.inline("🖥 حساب من", b"menu_account"), Button.inline("❓ راهنما", b"menu_help")],
        [Button.inline("✉️ پشتیبانی", b"menu_support")],
    ]
    if user_id in ADMIN_IDS:
        rows.append([Button.inline("⚙️ پنل مدیریت", b"admin_panel")])
    return rows
 
 
async def send_main_menu(event, edit=False):
    user = await event.get_sender()
    name = user.first_name or "کاربر"
    text = f"{FALLBACK}  خوش آمدید {name}!\n" + "─" * 18 + \
           "\n\n📨  با این ربات می‌تونید ایموجی‌های پرمیوم رو\nدر هر چت تلگرامی ارسال کنید!" \
           "\n\n🔖  از منوی زیر استفاده کنید:"
    text, ent = premiumize(text)
    ent.append(types.MessageEntityCustomEmoji(offset=0, length=1, document_id=EMOJI["rocket"]))
    buttons = main_menu_buttons(event.sender_id)
    if edit:
        await event.edit(text, formatting_entities=ent, buttons=buttons, parse_mode=None)
    else:
        await event.reply(text, formatting_entities=ent, buttons=buttons, parse_mode=None)
 
 
# =================================================================================
# استارت + دیپ‌لینک اشتراک ست (start=set_XXXXXXX)
# =================================================================================
@client.on(events.NewMessage(pattern=r"/start(?:\s+(.+))?$", func=lambda e: e.is_private))
async def on_start(event):
    user = await event.get_sender()
    ensure_user(event.sender_id, user.first_name, user.username)
 
    arg = event.pattern_match.group(1)
    if arg and arg.startswith("set_"):
        code = arg[len("set_"):]
        owner = find_user_by_set_code(code)
        if not owner:
            await event.reply("⚠️ کد ست معتبر نیست یا منقضی شده.")
        else:
            src_emojis = list_saved_emojis(owner["user_id"])
            limit = user_limit(event.sender_id)
            added = 0
            for row in src_emojis:
                if limit is not None and user_emoji_count(event.sender_id) >= limit:
                    break
                add_saved_emoji(event.sender_id, row["name"], row["doc_id"])
                added += 1
            await event.reply(f"✅ {added} ایموجی از ست دریافتی به حساب شما اضافه شد.")
        return
 
    await send_main_menu(event)
 
 
@client.on(events.CallbackQuery(data=b"back_main"))
async def on_back_main(event):
    await event.answer()
    await send_main_menu(event, edit=True)
 
 
# =================================================================================
# بخش «ایموجی پریمیوم» (حالت اینلاین)
# =================================================================================
@client.on(events.CallbackQuery(data=b"menu_premium"))
async def on_menu_premium(event):
    await event.answer()
    text = (
        "✨  ارسال ایموجی پرمیوم\n" + "─" * 18 +
        "\n\n📝  یک پیام جدید در همین چت بفرست:\n\n"
        "⚡  چند ایموجی پرمیوم (همه را یکجا بفرست)\n"
        "یا کد عددی: [5792080508976373427]\n\n"
        "🎙  چند کد را با فاصله یا براکت جدا کن:\n"
        "[کد۱] [کد۲] [کد۳]\n\n"
        "🎙  بعدش می‌تونی اسم دلخواه انتخاب کنی\n"
        "(یا «پیش‌فرض» بزنی)"
    )
    await event.edit(
        text,
        buttons=[[Button.switch_inline("✨ رفتن به حالت اینلاین", query="", same_peer=False)],
                 [Button.inline("🔙 بازگشت", b"back_main")]],
    )
 
 
@client.on(events.InlineQuery())
async def on_inline(event):
    query = event.text.strip()
    b = event.builder
 
    if not query:
        await event.answer([
            b.article(
                title="✨ ارسال ایموجی پرمیوم",
                description="پیام خود را بنویسید...",
                text="مثال: hi [5350291836378307462]",
            )
        ], cache_time=0, private=True)
        return
 
    text, entities = parse_query(query)
    if not entities:
        await event.answer([
            b.article(
                title="⚠️ فرمت اشتباه",
                description="مثال: hi [5350291836378307462]",
                text="فرمت صحیح: متن [کد_ایموجی]",
            )
        ], cache_time=0, private=True)
        return
 
    preview = text[:50] + ("..." if len(text) > 50 else "")
 
    await event.answer([
        b.article(
            title=f"ارسال با {len(entities)} ایموجی پرمیوم ✨",
            description=preview,
            text=query,
            buttons=Button.inline("\u200c", b"_"),
        )
    ], cache_time=0, private=True)
 
 
def parse_query(query: str):
    matches = list(re.finditer(r"\[(\d+)\]", query))
    if not matches:
        return None, None
 
    text = ""
    entities = []
    last = 0
    for m in matches:
        text += query[last:m.start()]
        entities.append(types.MessageEntityCustomEmoji(
            offset=utf16_len(text),
            length=1,
            document_id=int(m.group(1)),
        ))
        text += FALLBACK
        last = m.end()
 
    text += query[last:]
    return text.strip(), entities
 
 
async def edit_inline_message(msg_id, text: str, entities: list):
    from telethon.tl.functions.messages import EditInlineBotMessageRequest
    request = EditInlineBotMessageRequest(id=msg_id, message=text, entities=entities)
 
    dc_id = msg_id.dc_id
    if dc_id == client.session.dc_id:
        await client(request)
    else:
        sender = await client._borrow_exported_sender(dc_id)
        try:
            await sender.send(request)
        finally:
            await client._return_exported_sender(sender)
 
 
@client.on(events.Raw(UpdateBotInlineSend))
async def on_send(event):
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
            print(f"Edit failed (attempt {attempt+1}): {e}")
 
 
# =================================================================================
# بخش «استخراج کد ایموجی» (از پیام مستقیم یا لینک پک - بدون هیچ محدودیتی)
# =================================================================================
@client.on(events.CallbackQuery(data=b"menu_extract"))
async def on_menu_extract(event):
    await event.answer()
    pending.pop(event.sender_id, None)
    text = (
        "📤  استخراج کد ایموجی پرمیوم\n" + "─" * 18 +
        "\n\n🅰  یک یا چند ایموجی پرمیوم برای من بفرست:\n\n"
        "🔷  توجه: ایموجی باید پرمیوم باشه\n"
        "(ایموجی‌های معمولی کد ندارن)\n\n"
        "🎙  چند ایموجی هم می‌تونی یکجا بفرستی"
    )
    await edit_deco(event, text, buttons=[
        [Button.inline("🎁 استخراج از لینک پک", b"extract_pack")],
        [Button.inline("🔙 بازگشت", b"back_main")],
    ])
 
 
@client.on(events.CallbackQuery(data=b"extract_pack"))
async def on_extract_pack(event):
    await event.answer()
    pending[event.sender_id] = {"action": "await_pack_link"}
    await event.edit(
        "🎁  لینک پک ایموجی پرمیوم رو بفرست:\nمثال: https://t.me/addemoji/PackName",
        buttons=[[Button.inline("🔙 بازگشت", b"menu_extract")]],
    )
 
 
async def fetch_pack_documents(short_name: str):
    result = await client(functions.messages.GetStickerSetRequest(
        stickerset=types.InputStickerSetShortName(short_name=short_name),
        hash=0,
    ))
    return result.documents
 
 
def build_numbered_chunk(docs, start_index=1):
    text = ""
    entities = []
    idx = start_index
    for doc in docs:
        alt = doc_alt(doc)
        prefix = f"{idx}. "
        text += prefix
        emoji_offset = utf16_len(text)
        entities.append(types.MessageEntityCustomEmoji(
            offset=emoji_offset, length=utf16_len(alt), document_id=doc.id,
        ))
        text += alt + "\n"
        id_str = f"[{doc.id}]"
        id_offset = utf16_len(text)
        text += id_str
        entities.append(types.MessageEntityCode(offset=id_offset, length=utf16_len(id_str)))
        text += "\n" + ("─" * 10) + "\n"
        idx += 1
    return text, entities, idx
 
 
@client.on(events.NewMessage(func=lambda e: e.is_private and pending.get(e.sender_id, {}).get("action") == "await_pack_link"))
async def on_pack_link_input(event):
    match = PACK_LINK_RE.search(event.raw_text or "")
    if not match:
        await event.reply("⚠️ لینک معتبر پک ایموجی نیست. دوباره تلاش کن یا لینک کامل addemoji/... بفرست.")
        return
    pending.pop(event.sender_id, None)
    short_name = match.group(1)
 
    status = await event.reply("⏳ در حال دریافت پک...")
    try:
        docs = await fetch_pack_documents(short_name)
    except Exception as e:
        await status.edit(f"❌ خطا در دریافت پک: {e}")
        return
 
    if not docs:
        await status.edit("⚠️ پک خالی است یا معتبر نیست.")
        return
 
    CHUNK = 40
    idx = 1
    for i in range(0, len(docs), CHUNK):
        chunk_docs = docs[i:i + CHUNK]
        text, entities, idx = build_numbered_chunk(chunk_docs, idx)
        try:
            await client.send_message(event.chat_id, text, formatting_entities=entities, parse_mode=None)
        except Exception as e:
            await event.reply(f"❌ خطا در ارسال بخشی از نتایج: {e}")
        await asyncio.sleep(0.3)
 
    await status.edit(f"✅ استخراج {len(docs)} ایموجی از پک «{short_name}» انجام شد.\n(بدون محدودیت تعداد)")
 
 
# پیام مستقیم حاوی ایموجی پرمیوم (خارج از هر state دیگر) -> استخراج تکی/چندتایی
@client.on(events.NewMessage(func=lambda e: e.is_private and e.sender_id not in pending and extract_entities_from_message(e)))
async def on_direct_emoji_message(event):
    docs_ids = extract_entities_from_message(event)
    text = f"🅰  {len(docs_ids)} ایموجی پرمیوم شناسایی شد:\n\n"
    for did in docs_ids:
        text += f"`{did}`\n"
    await event.reply(text)
 
 
# =================================================================================
# بخش «ایموجی‌های من» (ذخیره‌سازی شخصی، محدودیت ۵۰تایی)
# =================================================================================
PAGE_SIZE = 5
 
 
def render_my_emojis_page(user_id, page=0):
    rows = list_saved_emojis(user_id)
    total = len(rows)
    limit = user_limit(user_id)
    limit_txt = "نامحدود" if limit is None else str(limit)
 
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(0, min(page, total_pages - 1))
    page_rows = rows[page * PAGE_SIZE: (page + 1) * PAGE_SIZE]
 
    text = f"⭐  ایموجی‌های ذخیره‌شده: {total}/{limit_txt}\n" + "─" * 18 + "\n\n"
    entities = []

    if not page_rows:
        text += "هنوز ایموجی‌ای ذخیره نکردی."
    else:
        # لیست واقعی ایموجی‌های ذخیره‌شده‌ی همین صفحه، همراه با خودِ ایموجی پرمیوم
        # (این کار فقط در متن پیام ممکن است؛ دکمه‌های inline توانایی حمل این entity را ندارند)
        for i, r in enumerate(page_rows, start=1):
            alt = r["alt"] if r["alt"] else FALLBACK
            text += f"{i}. "
            offset = utf16_len(text)
            entities.append(types.MessageEntityCustomEmoji(
                offset=offset, length=utf16_len(alt), document_id=r["doc_id"],
            ))
            text += f"{alt}  {r['name']}\n"
 
    buttons = []
    for r in page_rows:
        alt = r["alt"] if r["alt"] else FALLBACK
        # توجه: تلگرام اجازه نمی‌دهد برچسبِ دکمه‌ها entity داشته باشند، پس این‌جا فقط
        # می‌توانیم گلیفِ ساده‌ی fallback ایموجی را نشان دهیم، نه خودِ ایموجی پرمیوم واقعی.
        buttons.append([
            Button.inline(f"{alt} {r['name']}", f"noop".encode()),
            Button.inline("🗑 حذف", f"del_emoji_{r['id']}".encode()),
        ])
 
    nav_row = [
        Button.inline(f"{page+1}/{total_pages}", b"noop"),
        Button.inline("➡️ بعدی", f"myemo_page_{page+1}".encode()),
    ]
    buttons.append(nav_row)
    buttons.append([Button.inline("✏️ افزودن ایموجی", b"add_emoji_start")])
    buttons.append([Button.inline("🔙 بازگشت", b"menu_account")])
    return text, entities, buttons
 
 
@client.on(events.CallbackQuery(data=b"menu_my_emojis"))
async def on_my_emojis(event):
    await event.answer()
    text, ent, buttons = render_my_emojis_page(event.sender_id, 0)
    await event.edit(text, formatting_entities=ent, buttons=buttons, parse_mode=None)
 
 
@client.on(events.CallbackQuery(pattern=b"myemo_page_(\\d+)"))
async def on_my_emojis_page(event):
    await event.answer()
    page = int(event.pattern_match.group(1))
    text, ent, buttons = render_my_emojis_page(event.sender_id, page)
    await event.edit(text, formatting_entities=ent, buttons=buttons, parse_mode=None)
 
 
@client.on(events.CallbackQuery(pattern=b"del_emoji_(\\d+)"))
async def on_del_emoji(event):
    row_id = int(event.pattern_match.group(1))
    delete_saved_emoji(row_id, event.sender_id)
    await event.answer("🗑 حذف شد")
    text, ent, buttons = render_my_emojis_page(event.sender_id, 0)
    await event.edit(text, formatting_entities=ent, buttons=buttons, parse_mode=None)
 
 
@client.on(events.CallbackQuery(data=b"noop"))
async def on_noop(event):
    await event.answer()
 
 
@client.on(events.CallbackQuery(data=b"add_emoji_start"))
async def on_add_emoji_start(event):
    limit = user_limit(event.sender_id)
    if limit is not None and user_emoji_count(event.sender_id) >= limit:
        await event.answer(f"⛔️ به سقف {limit} ایموجی رسیدی. برای افزایش با پشتیبانی تماس بگیر.", alert=True)
        return
    await event.answer()
    pending[event.sender_id] = {"action": "await_add_emoji_id"}
    await event.edit(
        "✏️  ایموجی پرمیوم مورد نظر رو بفرست (خودِ ایموجی یا کد به‌صورت [آیدی]):",
        buttons=[[Button.inline("🔙 لغو", b"menu_my_emojis")]],
    )
 
 
@client.on(events.NewMessage(func=lambda e: e.is_private and pending.get(e.sender_id, {}).get("action") == "await_add_emoji_id"))
async def on_add_emoji_id_input(event):
    pairs = extract_emojis_with_alt(event)
    if not pairs:
        codes = parse_codes_from_text(event.raw_text or "")
        pairs = [(c, FALLBACK) for c in codes]
    if not pairs:
        await event.reply("⚠️ ایموجی پرمیوم یا کد معتبری پیدا نشد. دوباره امتحان کن.")
        return
 
    doc_id, alt = pairs[0]
    # فقط وارد state «منتظر اسم» می‌شویم؛ هنوز هیچ‌چیزی در دیتابیس ذخیره نمی‌شود
    # تا زمانی که کاربر اسم دلخواه را در پیام بعدی بفرستد.
    pending[event.sender_id] = {"action": "await_add_emoji_name", "doc_id": doc_id, "alt": alt}
    ent = [types.MessageEntityCustomEmoji(offset=0, length=utf16_len(alt), document_id=doc_id)]
    await event.reply(f"{alt}  حالا یک اسم دلخواه برای این ایموجی بفرست (یا «پیش‌فرض» بزن):",
                       formatting_entities=ent, parse_mode=None)
 
 
@client.on(events.NewMessage(func=lambda e: e.is_private and pending.get(e.sender_id, {}).get("action") == "await_add_emoji_name"))
async def on_add_emoji_name_input(event):
    # این هندلر تنها زمانی اجرا می‌شود که پیام بعدی (اسم) واقعاً رسیده باشد؛
    # یعنی ذخیره‌سازی همیشه *بعد* از دریافت اسم اتفاق می‌افتد، نه قبل از آن.
    state = pending.pop(event.sender_id)
    doc_id = state["doc_id"]
    alt = state.get("alt", FALLBACK)
    name = (event.raw_text or "").strip()
    if not name or name in ("پیش‌فرض", "پیشفرض"):
        name = f"ایموجی #{doc_id}"
 
    limit = user_limit(event.sender_id)
    if limit is not None and user_emoji_count(event.sender_id) >= limit:
        await event.reply(f"⛔️ به سقف {limit} ایموجی رسیدی.")
        return
 
    add_saved_emoji(event.sender_id, name, doc_id, alt)
    ent = [types.MessageEntityCustomEmoji(offset=0, length=utf16_len(alt), document_id=doc_id)]
    await event.reply(f"{alt} «{name}» ذخیره شد ✅", formatting_entities=ent, parse_mode=None,
                       buttons=[[Button.inline("⭐ ایموجی‌های من", b"menu_my_emojis")]])
 
 
# =================================================================================
# بخش «حساب من»
# =================================================================================
def account_menu_buttons():
    return [
        [Button.inline("⭐ ایموجی‌های من", b"menu_my_emojis"), Button.inline("📊 آمار من", b"my_stats")],
        [Button.inline("📋 کانال‌های من", b"menu_channels"), Button.inline("⭐ اشتراک ست من", b"my_set")],
        [Button.inline("🔙 بازگشت", b"back_main")],
    ]
 
 
@client.on(events.CallbackQuery(data=b"menu_account"))
async def on_menu_account(event):
    await event.answer()
    user = await event.get_sender()
    ensure_user(event.sender_id, user.first_name, user.username)
    u = get_user(event.sender_id)
    limit = user_limit(event.sender_id)
    limit_txt = "نامحدود" if limit is None else str(limit)
    count = user_emoji_count(event.sender_id)
    kind = "کاربر ویژه (نامحدود)" if u["unlimited"] else "کاربر عادی"
 
    text = (
        f"💠  حساب کاربری شما\n" + "─" * 18 +
        f"\n\n◁ آیدی: {event.sender_id}"
        f"\n◁ نام: {user.first_name or '-'}"
        f"\n◁ یوزرنیم: @{user.username or '-'}"
        f"\n◁ کاربر: {kind}"
        f"\n📈 ایموجی‌های ذخیره‌شده: {count}/{limit_txt}"
    )
    await edit_deco(event, text, buttons=account_menu_buttons())
 
 
@client.on(events.CallbackQuery(data=b"my_stats"))
async def on_my_stats(event):
    await event.answer()
    count = user_emoji_count(event.sender_id)
    channels = len(list_channels(event.sender_id))
    text = (
        "📊  آمار شما\n" + "─" * 18 +
        f"\n\n⭐ تعداد ایموجی ذخیره‌شده: {count}"
        f"\n📋 تعداد کانال‌های ثبت‌شده: {channels}"
    )
    await edit_deco(event, text, buttons=[[Button.inline("🔙 بازگشت", b"menu_account")]])
 
 
@client.on(events.CallbackQuery(data=b"my_set"))
async def on_my_set(event):
    await event.answer()
    code = get_or_create_set_code(event.sender_id)
    count = user_emoji_count(event.sender_id)
    me = await client.get_me()
    link = f"https://t.me/{me.username}?start=set_{code}"
    text = (
        "✅  ست شما آماده اشتراک شد!\n" + "─" * 18 +
        f"\n\n⭐ {count} ایموجی"
        f"\n◁ کد ست: {code}"
        f"\n\n🎙  دوستت این لینک رو باز کنه تا کل ست رو یکجا بگیره:\n{link}"
    )
    await edit_deco(event, text, buttons=[
        [Button.inline("⭐ کپی لینک", f"copy_set_{code}".encode())],
        [Button.inline("🔙 بازگشت", b"menu_account")],
    ])
 
 
@client.on(events.CallbackQuery(pattern=b"copy_set_(.+)"))
async def on_copy_set(event):
    code = event.pattern_match.group(1).decode()
    me = await client.get_me()
    link = f"https://t.me/{me.username}?start=set_{code}"
    await event.answer(f"لینک: {link}", alert=True)
 
 
# =================================================================================
# بخش «کانال‌های من» / افزودن کانال + تبدیل خودکار کد در پست‌ها
# =================================================================================
@client.on(events.CallbackQuery(data=b"menu_channels"))
async def on_menu_channels(event):
    await event.answer()
    chans = list_channels(event.sender_id)
    text = (
        "⌘  کانال‌های من\n" + "─" * 18 +
        "\n\n🎙  پست‌های حاوی کد ایموجی در کانال‌های فعال\nخودکار به ایموجی پرمیوم تبدیل می‌شوند.\n"
    )
    if not chans:
        text += "\n◁ هنوز کانالی ثبت نکردید."
    else:
        text += "\n" + "\n".join(f"◁ {c['title'] or c['channel_id']}" for c in chans)
 
    await edit_deco(event, text, buttons=[
        [Button.inline("✏️ افزودن کانال", b"add_channel_start")],
        [Button.inline("🔙 بازگشت", b"menu_account")],
    ])
 
 
@client.on(events.CallbackQuery(data=b"add_channel_start"))
async def on_add_channel_start(event):
    await event.answer()
    pending[event.sender_id] = {"action": "await_channel_id"}
    text = (
        "✈️  افزودن کانال\n" + "─" * 18 +
        "\n\n📨  ابتدا ربات را در کانال خود ادمین کنید با این دسترسی‌ها:\n\n"
        "⚡ افزودن اعضا (دعوت با لینک)\n"
        "⚡ افزودن ادمین\n"
        "⚡ ویرایش پیام‌ها\n\n"
        f"🎙  کانال باید حداقل {CHANNEL_MIN_MEMBERS} عضو داشته باشد.\n\n"
        "📨  سپس آیدی عددی یا یوزرنیم کانال را بفرستید:\nمثل @my_channel یا -1001234567890"
    )
    await edit_deco(event, text, buttons=[[Button.inline("🔙 بازگشت", b"menu_channels")]])
 
 
@client.on(events.NewMessage(func=lambda e: e.is_private and pending.get(e.sender_id, {}).get("action") == "await_channel_id"))
async def on_channel_id_input(event):
    pending.pop(event.sender_id, None)
    raw = (event.raw_text or "").strip()
    try:
        entity = await client.get_entity(raw)
    except Exception as e:
        await event.reply(f"❌ کانال پیدا نشد: {e}")
        return
 
    if not isinstance(entity, types.Channel):
        await event.reply("⚠️ این یک کانال معتبر نیست.")
        return
 
    try:
        full = await client(functions.channels.GetFullChannelRequest(entity))
        members_count = full.full_chat.participants_count or 0
    except Exception:
        members_count = 0
 
    if members_count and members_count < CHANNEL_MIN_MEMBERS:
        await event.reply(f"⚠️ کانال باید حداقل {CHANNEL_MIN_MEMBERS} عضو داشته باشد (فعلی: {members_count}).")
        return
 
    try:
        me = await client.get_permissions(entity, "me")
        if not (me.is_admin and getattr(me, "edit_messages", False)):
            await event.reply("⚠️ ربات باید در این کانال ادمین باشد و دسترسی «ویرایش پیام‌ها» داشته باشد.")
            return
    except Exception as e:
        await event.reply(f"❌ نمی‌توانم دسترسی‌های ربات در کانال را بررسی کنم: {e}")
        return
 
    ok = add_channel(event.sender_id, entity.id, entity.title)
    if not ok:
        await event.reply("⚠️ این کانال قبلا ثبت شده است.")
        return
 
    await event.reply(f"✅ کانال «{entity.title}» با موفقیت ثبت شد.\nاز این پس کدهای [آیدی] در پست‌های این کانال خودکار به ایموجی تبدیل می‌شوند.")
 
 
@client.on(events.NewMessage(func=lambda e: (not e.is_private) and e.raw_text and CODE_RE.search(e.raw_text)))
async def on_channel_post(event):
    chat = await event.get_chat()
    if not isinstance(chat, types.Channel):
        return
    if not is_registered_channel(chat.id):
        return
 
    text, entities = parse_query(event.raw_text)
    if not entities:
        return
 
    try:
        # نکته‌ی مهم: parse_mode باید صراحتاً None باشد وگرنه Telethon سعی می‌کند متن را
        # دوباره با پارسر پیش‌فرض (مثلا مارک‌داون) تفسیر کند و entityهای دستی‌ای که خودمان
        # برای هر آیدی جداگانه ساختیم را نادیده می‌گیرد؛ نتیجه‌اش این بود که فارغ از این‌که
        # کاربر چه آیدی‌ای فرستاده، فقط همان کاراکتر ⭐ (ثابت در FALLBACK) به‌عنوان متن ساده
        # باقی می‌ماند و هیچ ایموجی پرمیومی واقعی جایگزین نمی‌شد.
        await client.edit_message(
            chat, event.message.id, text,
            formatting_entities=entities,
            parse_mode=None,
        )
    except Exception as e:
        print(f"channel auto-convert failed: {e}")
 
 
# =================================================================================
# بخش راهنما
# =================================================================================
@client.on(events.CallbackQuery(data=b"menu_help"))
async def on_help(event):
    await event.answer()
    text = (
        "❓  راهنمای ربات\n" + "─" * 18 +
        "\n\n1️⃣ برای ارسال ایموجی پرمیوم در چت‌های دیگر، از حالت اینلاین استفاده کن:\n"
        "@your_bot متن [آیدی_ایموجی]\n\n"
        "2️⃣ برای استخراج آیدی همه ایموجی‌های یک پک، لینک پک را برای ربات بفرست.\n\n"
        "3️⃣ در «ایموجی‌های من» می‌تونی ایموجی‌های پرکاربردت رو ذخیره کنی.\n\n"
        "4️⃣ با افزودن کانال، پست‌های حاوی کد به‌صورت خودکار تبدیل می‌شوند."
    )
    await edit_deco(event, text, buttons=[[Button.inline("🔙 بازگشت", b"back_main")]])
 
 
# =================================================================================
# بخش پشتیبانی (بدون پیوی مستقیم) + ارسال تیکت
# =================================================================================
@client.on(events.CallbackQuery(data=b"menu_support"))
async def on_support(event):
    await event.answer()
    text = (
        "💎  پشتیبانی\n" + "─" * 18 +
        "\n\n📨  برای ارتباط با پشتیبانی یکی از روش‌های زیر را انتخاب کن:\n\n"
        "⚡ پیوی پشتیبانی:\nپیام خود را همینجا بفرست، پشتیبانی از طریق ربات پاسخ می‌دهد\n\n"
        "🕐 ارسال تیکت:\nپیام خود را ثبت کن تا پشتیبانی پاسخ دهد"
    )
    await edit_deco(event, text, buttons=[
        [Button.inline("🦖 پیوی پشتیبانی", b"support_chat"), Button.inline("🖼 ارسال تیکت", b"support_ticket")],
        [Button.inline("🔙 بازگشت", b"back_main")],
    ])
 
 
@client.on(events.CallbackQuery(data=b"support_chat"))
async def on_support_chat(event):
    await event.answer()
    pending[event.sender_id] = {"action": "await_support_msg"}
    await event.edit(
        "📨 پیام خودت رو بنویس، مستقیم (فقط از طریق ربات) برای پشتیبانی ارسال می‌شود:",
        buttons=[[Button.inline("🔙 لغو", b"menu_support")]],
    )
 
 
@client.on(events.NewMessage(func=lambda e: e.is_private and pending.get(e.sender_id, {}).get("action") == "await_support_msg"))
async def on_support_msg_input(event):
    pending.pop(event.sender_id, None)
    user = await event.get_sender()
    msg = event.raw_text or ""
    for admin_id in ADMIN_IDS:
        await safe_send(
            admin_id,
            f"✉️ پیام پشتیبانی جدید\nاز: {user.first_name or ''} (@{user.username or '-'}) | ID: {event.sender_id}\n\n{msg}\n\n"
            f"↩️ برای پاسخ: /reply {event.sender_id} متن_پاسخ",
        )
    await event.reply("✅ پیام شما برای پشتیبانی ارسال شد. منتظر پاسخ باشید.")
 
 
@client.on(events.NewMessage(pattern=r"/reply (\d+) (.+)", func=lambda e: e.is_private and e.sender_id in ADMIN_IDS))
async def on_admin_reply(event):
    target_id = int(event.pattern_match.group(1))
    text = event.pattern_match.group(2)
    ok = await safe_send(target_id, f"💎 پاسخ پشتیبانی:\n\n{text}")
    await event.reply("✅ ارسال شد." if ok else "❌ ارسال نشد (کاربر ربات را بلاک کرده).")
 
 
@client.on(events.CallbackQuery(data=b"support_ticket"))
async def on_support_ticket(event):
    await event.answer()
    pending[event.sender_id] = {"action": "await_ticket_msg"}
    await event.edit(
        "🖼 متن تیکت خودت رو بنویس تا ثبت بشه:",
        buttons=[[Button.inline("🔙 لغو", b"menu_support")]],
    )
 
 
@client.on(events.NewMessage(func=lambda e: e.is_private and pending.get(e.sender_id, {}).get("action") == "await_ticket_msg"))
async def on_ticket_msg_input(event):
    pending.pop(event.sender_id, None)
    add_ticket(event.sender_id, event.raw_text or "")
    user = await event.get_sender()
    for admin_id in ADMIN_IDS:
        await safe_send(
            admin_id,
            f"🎫 تیکت جدید\nاز: {user.first_name or ''} (@{user.username or '-'}) | ID: {event.sender_id}\n\n{event.raw_text}",
        )
    await event.reply("✅ تیکت شما ثبت شد. به‌زودی بررسی می‌شود.")
 
 
# =================================================================================
# پنل مدیریت
# =================================================================================
def is_admin(user_id):
    return user_id in ADMIN_IDS
 
 
@client.on(events.CallbackQuery(data=b"admin_panel"))
async def on_admin_panel(event):
    if not is_admin(event.sender_id):
        await event.answer("⛔️ شما به این بخش دسترسی ندارید.", alert=True)
        return
    await event.answer()
    await event.edit(
        "⚙️  پنل مدیریت\n" + "─" * 18,
        buttons=[
            [Button.inline("📊 آمار دقیق", b"admin_stats")],
            [Button.inline("🔓 حذف محدودیت کاربر", b"admin_unlimit")],
            [Button.inline("📢 ارسال پیام همگانی", b"admin_broadcast")],
            [Button.inline("🔙 بازگشت", b"back_main")],
        ],
    )
 
 
@client.on(events.CallbackQuery(data=b"admin_stats"))
async def on_admin_stats(event):
    if not is_admin(event.sender_id):
        await event.answer("⛔️ دسترسی ندارید.", alert=True)
        return
    await event.answer()
    s = stats()
    text = (
        "📊  آمار دقیق ربات\n" + "─" * 18 +
        f"\n\n👥 کاربران: {s['users']}"
        f"\n⭐ کل ایموجی‌های ذخیره‌شده: {s['emojis']}"
        f"\n📋 کانال‌های ثبت‌شده: {s['channels']}"
        f"\n🎫 تیکت‌های باز: {s['open_tickets']}"
        f"\n🔓 کاربران نامحدود: {s['unlimited_users']}"
    )
    await edit_deco(event, text, buttons=[[Button.inline("🔙 بازگشت", b"admin_panel")]])
 
 
@client.on(events.CallbackQuery(data=b"admin_unlimit"))
async def on_admin_unlimit(event):
    if not is_admin(event.sender_id):
        await event.answer("⛔️ دسترسی ندارید.", alert=True)
        return
    await event.answer()
    pending[event.sender_id] = {"action": "await_unlimit_target"}
    await event.edit(
        "🔓 آیدی عددی کاربری که می‌خوای محدودیتش برداشته بشه رو بفرست:",
        buttons=[[Button.inline("🔙 لغو", b"admin_panel")]],
    )
 
 
@client.on(events.NewMessage(func=lambda e: e.is_private and e.sender_id in ADMIN_IDS and pending.get(e.sender_id, {}).get("action") == "await_unlimit_target"))
async def on_unlimit_target_input(event):
    pending.pop(event.sender_id, None)
    raw = (event.raw_text or "").strip()
    if not raw.isdigit():
        await event.reply("⚠️ آیدی عددی معتبر بفرست.")
        return
    target_id = int(raw)
    ensure_user(target_id)
    cur = _conn.cursor()
    cur.execute("UPDATE users SET unlimited=1 WHERE user_id=?", (target_id,))
    _conn.commit()
    await event.reply(f"✅ محدودیت کاربر {target_id} برداشته شد (نامحدود شد).")
    await safe_send(target_id, "🎉 محدودیت ذخیره‌سازی ایموجی شما توسط ادمین برداشته شد و اکنون نامحدود است.")
 
 
@client.on(events.CallbackQuery(data=b"admin_broadcast"))
async def on_admin_broadcast(event):
    if not is_admin(event.sender_id):
        await event.answer("⛔️ دسترسی ندارید.", alert=True)
        return
    await event.answer()
    pending[event.sender_id] = {"action": "await_broadcast_msg"}
    await event.edit(
        "📢 متن پیام همگانی رو بفرست تا برای همه کاربران ارسال بشه:",
        buttons=[[Button.inline("🔙 لغو", b"admin_panel")]],
    )
 
 
@client.on(events.NewMessage(func=lambda e: e.is_private and e.sender_id in ADMIN_IDS and pending.get(e.sender_id, {}).get("action") == "await_broadcast_msg"))
async def on_broadcast_msg_input(event):
    pending.pop(event.sender_id, None)
    text = event.raw_text or ""
    ids = all_user_ids()
    status = await event.reply(f"⏳ در حال ارسال به {len(ids)} کاربر...")
    sent, failed = 0, 0
    for uid in ids:
        ok = await safe_send(uid, f"📢 پیام همگانی:\n\n{text}")
        if ok:
            sent += 1
        else:
            failed += 1
        await asyncio.sleep(0.05)
    await status.edit(f"✅ ارسال شد.\nموفق: {sent} | ناموفق: {failed}")
 
 
print("Bot started...")
client.run_until_disconnected()
 
