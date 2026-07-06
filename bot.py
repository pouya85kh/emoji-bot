import os
import re
import asyncio
from telethon import TelegramClient, events, Button
from telethon.tl import types, functions
from telethon.tl.types import UpdateBotInlineSend
 
# ================= تنظیمات =================
API_ID    = int(os.environ["API_ID"])
API_HASH  = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]
 
ADMIN_IDS = {7049497099}          # آیدی عددی ادمین‌ها را اینجا بگذار
SUPPORT_USERNAME = "nooooofear" # بدون @
 
FALLBACK = "\u2b50"
 
# آیدی عددی چند ایموجی پرمیوم که خودت مالک/دسترسی به آن‌ها را داری
# برای تزئین منو استفاده می‌شود (باید واقعی و معتبر باشند وگرنه ارسال fail می‌شود)
DECO_EMOJI_ID = 5782898040696214721
 
client = TelegramClient("bot", API_ID, API_HASH).start(bot_token=BOT_TOKEN)
 
PACK_LINK_RE = re.compile(r"(?:addemoji|addstickers)/([a-zA-Z0-9_]+)")
 
 
def utf16_len(text: str) -> int:
    return len(text.encode("utf-16-le")) // 2
 
 
# ================= بخش قبلی: پارس ایموجی از کوئری اینلاین =================
def parse(query: str) -> tuple[str | None, list | None]:
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
 
 
async def edit(msg_id, text: str, entities: list):
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
 
 
@client.on(events.InlineQuery())
async def on_inline(event):
    query = event.text.strip()
    b = event.builder
 
    if not query:
        await event.answer([
            b.article(
                title="✨ ارسال ایموجی پریمیوم",
                description="پیام خود را بنویسید...",
                text="مثال: hi [5350291836378307462]",
            )
        ], cache_time=0, private=True)
        return
 
    text, entities = parse(query)
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
            title=f"ارسال با {len(entities)} ایموجی پریمیوم ✨",
            description=preview,
            text=query,
            buttons=Button.inline("\u200c", b"_"),
        )
    ], cache_time=0, private=True)
 
 
@client.on(events.Raw(UpdateBotInlineSend))
async def on_send(event):
    if not event.msg_id:
        return
 
    query = (event.query or "").strip()
    text, entities = parse(query)
    if not entities:
        return
 
    for attempt in range(3):
        try:
            await asyncio.sleep(0.4 * (attempt + 1))
            await edit(event.msg_id, text, entities)
            return
        except Exception as e:
            print(f"Edit failed (attempt {attempt+1}): {e}")
 
 
# ================= بخش جدید: استخراج آیدی از لینک پک ایموجی پرمیوم =================
async def fetch_pack_documents(short_name: str):
    result = await client(functions.messages.GetStickerSetRequest(
        stickerset=types.InputStickerSetShortName(short_name=short_name),
        hash=0,
    ))
    return result.documents
 
 
def doc_alt(doc) -> str:
    for attr in doc.attributes:
        if isinstance(attr, types.DocumentAttributeCustomEmoji):
            return attr.alt or FALLBACK
    return FALLBACK
 
 
def build_chunk(docs) -> tuple[str, list]:
    text = ""
    entities = []
    for doc in docs:
        alt = doc_alt(doc)
        entities.append(types.MessageEntityCustomEmoji(
            offset=utf16_len(text),
            length=utf16_len(alt),
            document_id=doc.id,
        ))
        text += alt
        text += "  →  "
        id_start = utf16_len(text)
        id_str = str(doc.id)
        text += id_str
        entities.append(types.MessageEntityCode(
            offset=id_start,
            length=utf16_len(id_str),
        ))
        text += "\n"
    return text, entities
 
 
async def send_raw(chat_id, text, entities):
    from telethon.tl.functions.messages import SendMessageRequest
    await client(SendMessageRequest(
        peer=await client.get_input_entity(chat_id),
        message=text,
        entities=entities,
        random_id=int.from_bytes(bytes(8), "big") or __import__("random").getrandbits(63),
    ))
 
 
@client.on(events.NewMessage(func=lambda e: e.is_private and bool(PACK_LINK_RE.search(e.raw_text or ""))))
async def on_pack_link(event):
    match = PACK_LINK_RE.search(event.raw_text)
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
    for i in range(0, len(docs), CHUNK):
        chunk_docs = docs[i:i + CHUNK]
        text, entities = build_chunk(chunk_docs)
        try:
            await client.send_message(event.chat_id, text, formatting_entities=entities)
        except Exception as e:
            await event.reply(f"❌ خطا در ارسال بخشی از نتایج: {e}")
        await asyncio.sleep(0.3)
 
    await status.edit(f"✅ استخراج {len(docs)} ایموجی از پک «{short_name}» انجام شد.")
 
 
# ================= منو / دکمه‌های شیشه‌ای =================
def main_menu_buttons():
    return [
        [Button.inline("📦 استخراج آیدی پک ایموجی", b"how_extract")],
        [Button.inline("❓ راهنما", b"help"), Button.inline("🛠 پشتیبانی", b"support")],
    ]
 
 
async def send_main_menu(event, edit=False):
    header_text = FALLBACK + "  منوی ربات\n\nیکی از گزینه‌های زیر را انتخاب کنید:"
    header_entities = [types.MessageEntityCustomEmoji(offset=0, length=1, document_id=DECO_EMOJI_ID)]
 
    buttons = main_menu_buttons()
    if event.sender_id in ADMIN_IDS:
        buttons.append([Button.inline("⚙️ پنل مدیریت", b"admin_panel")])
 
    if edit:
        await event.edit(header_text, formatting_entities=header_entities, buttons=buttons)
    else:
        await event.reply(header_text, formatting_entities=header_entities, buttons=buttons)
 
 
@client.on(events.NewMessage(pattern="/start", func=lambda e: e.is_private))
async def on_start(event):
    await send_main_menu(event)
 
 
@client.on(events.CallbackQuery(data=b"help"))
async def on_help(event):
    await event.answer()
    text = (
        "راهنمای ربات:\n\n"
        "1️⃣ برای ارسال ایموجی پرمیوم در چت‌های دیگر، از حالت اینلاین استفاده کن:\n"
        "@your_bot متن [آیدی_ایموجی]\n\n"
        "2️⃣ برای استخراج آیدی همه ایموجی‌های یک پک، لینک پک را همینجا برای ربات بفرست:\n"
        "مثال: https://t.me/addemoji/PackName"
    )
    await event.respond(text, buttons=[[Button.inline("🔙 بازگشت", b"back_main")]])
 
 
@client.on(events.CallbackQuery(data=b"support"))
async def on_support(event):
    await event.answer()
    await event.respond(
        "برای پشتیبانی با آیدی زیر در ارتباط باشید:",
        buttons=[
            [Button.url("💬 ارتباط با پشتیبانی", f"https://t.me/{SUPPORT_USERNAME}")],
            [Button.inline("🔙 بازگشت", b"back_main")],
        ],
    )
 
 
@client.on(events.CallbackQuery(data=b"how_extract"))
async def on_how_extract(event):
    await event.answer()
    await event.respond(
        "فقط کافیه لینک پک ایموجی پرمیوم رو مستقیم برام بفرستی، مثلا:\n"
        "https://t.me/addemoji/PackName\n\n"
        "و خروجی رو به صورت خودِ ایموجی + آیدی عددیش برات میفرستم.",
        buttons=[[Button.inline("🔙 بازگشت", b"back_main")]],
    )
 
 
@client.on(events.CallbackQuery(data=b"admin_panel"))
async def on_admin_panel(event):
    if event.sender_id not in ADMIN_IDS:
        await event.answer("⛔️ شما به این بخش دسترسی ندارید.", alert=True)
        return
    await event.answer()
    await event.respond(
        "⚙️ پنل مدیریت:",
        buttons=[
            [Button.inline("📊 آمار ربات", b"admin_stats")],
            [Button.inline("📢 ارسال پیام همگانی", b"admin_broadcast")],
            [Button.inline("🔙 بازگشت", b"back_main")],
        ],
    )
 
 
@client.on(events.CallbackQuery(data=b"admin_stats"))
async def on_admin_stats(event):
    if event.sender_id not in ADMIN_IDS:
        await event.answer("⛔️ دسترسی ندارید.", alert=True)
        return
    await event.answer()
    # TODO: آمار واقعی (تعداد کاربران و ...) را از دیتابیس خودت وصل کن
    await event.respond("📊 آمار ربات هنوز پیاده‌سازی نشده — این بخش را به دیتابیس خودت وصل کن.",
                         buttons=[[Button.inline("🔙 بازگشت", b"admin_panel")]])
 
 
@client.on(events.CallbackQuery(data=b"admin_broadcast"))
async def on_admin_broadcast(event):
    if event.sender_id not in ADMIN_IDS:
        await event.answer("⛔️ دسترسی ندارید.", alert=True)
        return
    await event.answer()
    await event.respond("📢 ارسال همگانی هنوز پیاده‌سازی نشده — نیاز به لیست کاربران در دیتابیس داری.",
                         buttons=[[Button.inline("🔙 بازگشت", b"admin_panel")]])
 
 
@client.on(events.CallbackQuery(data=b"back_main"))
async def on_back_main(event):
    await event.answer()
    await send_main_menu(event, edit=False)
 
 
print("Bot started...")
client.run_until_disconnected()
