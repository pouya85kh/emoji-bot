from __future__ import annotations

import asyncio
import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, InlineQuery, Message

from bot.callbacks import AccountCB, AdminCB, ChannelCB, EmojiActionCB, EmojiDeleteCB, EmojiPageCB, LanguageCB, MenuCB, MiscCB, SupportCB
from bot.keyboards import account_keyboard, admin_keyboard, channels_keyboard, emojis_keyboard, language_keyboard, main_menu_keyboard, support_keyboard
from bot.states import AdminFlow, ChannelFlow, EmojiFlow, ExtractFlow, StartFlow, SupportFlow
from bot.utils import PACK_LINK_RE

logger = logging.getLogger(__name__)
router = Router()


async def show_main_menu(event, app, locale: str, user_id: int, edit: bool = False) -> None:
    first_name = getattr(event.from_user, "first_name", None) or "User"
    text = app.localizer.get(locale, "menu.welcome", name=first_name)
    text, entities = app.emojis.premiumize(text)
    keyboard = main_menu_keyboard(locale, is_admin=user_id in app.settings.admin_ids)
    if isinstance(event, Message) and not edit:
        await event.answer(text, entities=entities or None, reply_markup=keyboard, parse_mode=None)
    else:
        await event.message.edit_text(text, entities=entities or None, reply_markup=keyboard, parse_mode=None)


async def show_premium_menu(message, app, locale: str, edit: bool = False) -> None:
    text = app.localizer.get(locale, "premium.title") + "\n" + "─" * 18 + "\n\n" + app.localizer.get(locale, "premium.body")
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✨ رفتن به حالت اینلاین" if locale == "fa" else "✨ Go inline", switch_inline_query="")],
        [InlineKeyboardButton(text="🔙 بازگشت" if locale == "fa" else "🔙 Back", callback_data=MenuCB(section="main").pack())],
    ])
    if edit:
        await message.edit_text(text, reply_markup=keyboard)
    else:
        await message.answer(text, reply_markup=keyboard)


async def show_extract_menu(message, app, locale: str, edit: bool = False) -> None:
    text = app.localizer.get(locale, "extract.title") + "\n" + "─" * 18 + "\n\n" + app.localizer.get(locale, "extract.body")
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 استخراج از لینک پک" if locale == "fa" else "🎁 Extract from pack link", callback_data="extract_pack")],
        [InlineKeyboardButton(text="🔙 بازگشت" if locale == "fa" else "🔙 Back", callback_data=MenuCB(section="main").pack())],
    ])
    if edit:
        await message.edit_text(text, reply_markup=keyboard)
    else:
        await message.answer(text, reply_markup=keyboard)


async def show_help_menu(message, app, locale: str, edit: bool = False) -> None:
    text = app.localizer.get(locale, "help.body")
    keyboard = main_menu_keyboard(locale, is_admin=message.chat.id in app.settings.admin_ids)
    if edit:
        await message.edit_text(text, reply_markup=keyboard)
    else:
        await message.answer(text, reply_markup=keyboard)


async def show_support_menu(message, app, locale: str, edit: bool = False) -> None:
    text = app.localizer.get(locale, "support.body")
    keyboard = support_keyboard(locale)
    if edit:
        await message.edit_text(text, reply_markup=keyboard)
    else:
        await message.answer(text, reply_markup=keyboard)


async def show_account_menu(callback: CallbackQuery, app, locale: str, user_id: int) -> None:
    user = callback.from_user
    await app.users.ensure(user_id, user.first_name, user.username)
    u = await app.db.get_user(user_id)
    limit = await app.emojis.limit(user_id)
    limit_txt = "نامحدود" if limit is None else str(limit)
    count = await app.emojis.count(user_id)
    kind = app.localizer.get(locale, "account.vip") if u and u.unlimited else app.localizer.get(locale, "account.normal")
    text = app.localizer.get(
        locale,
        "account.body",
        user_id=user_id,
        first_name=user.first_name or "-",
        username=user.username or "-",
        kind=kind,
        count=count,
        limit_txt=limit_txt,
    )
    text, entities = app.emojis.premiumize(text)
    await callback.message.edit_text(text, entities=entities or None, reply_markup=account_keyboard(locale), parse_mode=None)


async def show_channels_menu(message, app, locale: str, user_id: int, edit: bool = False) -> None:
    chans = await app.channels.list(user_id)
    text = app.localizer.get(locale, "channels.body")
    if chans:
        text += "\n\n" + "\n".join(f"◁ {c.title or c.channel_id}" for c in chans)
    else:
        text += "\n\n" + app.localizer.get(locale, "channels.empty")
    keyboard = channels_keyboard(locale)
    if edit:
        await message.edit_text(text, reply_markup=keyboard)
    else:
        await message.answer(text, reply_markup=keyboard)


async def show_admin_panel(message, app, locale: str, edit: bool = False) -> None:
    keyboard = admin_keyboard(locale)
    text = app.localizer.get(locale, "admin.panel")
    if edit:
        await message.edit_text(text, reply_markup=keyboard)
    else:
        await message.answer(text, reply_markup=keyboard)


@router.message(CommandStart())
async def start_handler(message: Message, state: FSMContext, app, locale: str | None):
    await app.users.ensure(message.from_user.id, message.from_user.first_name, message.from_user.username)
    payload = ""
    if message.text:
        parts = message.text.split(maxsplit=1)
        if len(parts) > 1:
            payload = parts[1].strip()

    if locale is None:
        await state.set_state(StartFlow.waiting_language)
        await state.update_data(start_payload=payload)
        await message.answer("Choose your language / زبان را انتخاب کنید", reply_markup=language_keyboard("start"))
        return

    if payload.startswith("set_"):
        code = payload.removeprefix("set_")
        owner = await app.emojis.owner_by_set_code(code)
        if not owner:
            await message.answer(app.localizer.get(locale, "start.invalid_set"))
            return
        added = await app.emojis.add_from_owner(message.from_user.id, owner.user_id)
        await message.answer(app.localizer.get(locale, "start.set_added", count=added))
        return

    await show_main_menu(message, app, locale, message.from_user.id, edit=False)


@router.callback_query(LanguageCB.filter())
async def language_select(callback: CallbackQuery, callback_data: LanguageCB, state: FSMContext, app, locale: str | None):
    await callback.answer()
    await app.users.set_locale(callback.from_user.id, callback_data.code)
    data = await state.get_data()
    payload = data.get("start_payload", "")
    await state.clear()

    if callback_data.next_action == "account":
        await show_account_menu(callback, app, callback_data.code, callback.from_user.id)
        return

    if payload.startswith("set_"):
        code = payload.removeprefix("set_")
        owner = await app.emojis.owner_by_set_code(code)
        if not owner:
            await callback.message.edit_text(app.localizer.get(callback_data.code, "start.invalid_set"), reply_markup=main_menu_keyboard(callback_data.code, callback.from_user.id in app.settings.admin_ids))
            return
        added = await app.emojis.add_from_owner(callback.from_user.id, owner.user_id)
        await callback.message.edit_text(app.localizer.get(callback_data.code, "start.set_added", count=added), reply_markup=main_menu_keyboard(callback_data.code, callback.from_user.id in app.settings.admin_ids))
        return

    await show_main_menu(callback, app, callback_data.code, callback.from_user.id, edit=True)


@router.callback_query(MenuCB.filter())
async def menu_router(callback: CallbackQuery, callback_data: MenuCB, app, locale: str):
    await callback.answer()
    section = callback_data.section
    if section == "main":
        await show_main_menu(callback, app, locale, callback.from_user.id, edit=True)
    elif section == "premium":
        await show_premium_menu(callback.message, app, locale, edit=True)
    elif section == "extract":
        await show_extract_menu(callback.message, app, locale, edit=True)
    elif section == "account":
        await show_account_menu(callback, app, locale, callback.from_user.id)
    elif section == "help":
        await show_help_menu(callback.message, app, locale, edit=True)
    elif section == "support":
        await show_support_menu(callback.message, app, locale, edit=True)
    elif section == "my_emojis":
        await show_my_emojis(callback.message, app, locale, callback.from_user.id, page=0, edit=True)
    elif section == "channels":
        await show_channels_menu(callback.message, app, locale, callback.from_user.id, edit=True)


@router.callback_query(AccountCB.filter())
async def account_actions(callback: CallbackQuery, callback_data: AccountCB, app, locale: str, state: FSMContext):
    await callback.answer()
    if callback_data.action == "stats":
        count = await app.emojis.count(callback.from_user.id)
        channels = len(await app.channels.list(callback.from_user.id))
        await callback.message.edit_text(app.localizer.get(locale, "account.stats", emojis=count, channels=channels), reply_markup=account_keyboard(locale))
    elif callback_data.action == "set":
        code = await app.emojis.get_or_create_set_code(callback.from_user.id)
        count = await app.emojis.count(callback.from_user.id)
        me = await app.bot.get_me()
        link = f"https://t.me/{me.username}?start=set_{code}"
        await callback.message.edit_text(app.localizer.get(locale, "account.set_link", count=count, code=code, link=link), reply_markup=account_keyboard(locale))
    elif callback_data.action == "change_lang":
        await callback.message.edit_text(app.localizer.get(locale, "language.change_prompt"), reply_markup=language_keyboard("account"))


@router.callback_query(EmojiPageCB.filter())
async def page_callback(callback: CallbackQuery, callback_data: EmojiPageCB, app, locale: str):
    await callback.answer()
    await show_my_emojis(callback.message, app, locale, callback.from_user.id, page=callback_data.page, edit=True)


@router.callback_query(EmojiDeleteCB.filter())
async def delete_callback(callback: CallbackQuery, callback_data: EmojiDeleteCB, app, locale: str):
    await app.emojis.delete(callback_data.row_id, callback.from_user.id)
    await callback.answer(app.localizer.get(locale, "emoji.deleted"))
    await show_my_emojis(callback.message, app, locale, callback.from_user.id, page=0, edit=True)


@router.callback_query(MiscCB.filter())
async def noop_callback(callback: CallbackQuery):
    await callback.answer()


@router.callback_query(EmojiActionCB.filter())
async def emoji_action(callback: CallbackQuery, callback_data: EmojiActionCB, state: FSMContext, app, locale: str):
    if callback_data.action != "add_start":
        await callback.answer()
        return
    limit = await app.emojis.limit(callback.from_user.id)
    count = await app.emojis.count(callback.from_user.id)
    if limit is not None and count >= limit:
        await callback.answer(app.localizer.get(locale, "emoji.limit_reached", limit=limit), show_alert=True)
        return
    await callback.answer()
    await state.set_state(EmojiFlow.waiting_emoji_id)
    await callback.message.edit_text(app.localizer.get(locale, "emoji.ask_id"), reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 لغو" if locale == "fa" else "🔙 Cancel", callback_data=MenuCB(section="my_emojis").pack())]]))


@router.message(EmojiFlow.waiting_emoji_id)
async def emoji_id_input(message: Message, state: FSMContext, app, locale: str):
    pairs = await app.emojis.extract_pairs(message)
    if not pairs:
        codes = await app.emojis.parse_codes(message.text)
        pairs = [(code, app.settings.fallback_emoji) for code in codes]
    if not pairs:
        await message.answer(app.localizer.get(locale, "emoji.invalid_id"))
        return
    doc_id, alt = pairs[0]
    await state.set_state(EmojiFlow.waiting_emoji_name)
    await state.update_data(doc_id=doc_id, alt=alt)
    await message.answer(app.localizer.get(locale, "emoji.ask_name", alt=alt))


@router.message(EmojiFlow.waiting_emoji_name)
async def emoji_name_input(message: Message, state: FSMContext, app, locale: str):
    data = await state.get_data()
    await state.clear()
    doc_id = int(data["doc_id"])
    alt = data.get("alt", app.settings.fallback_emoji)
    name = (message.text or "").strip()
    if not name or name.lower() in {"default", "پیش‌فرض", "پیشفرض"}:
        name = app.localizer.get(locale, "emoji.default_name", doc_id=doc_id)
    limit = await app.emojis.limit(message.from_user.id)
    count = await app.emojis.count(message.from_user.id)
    if limit is not None and count >= limit:
        await message.answer(app.localizer.get(locale, "emoji.limit_reached", limit=limit))
        return
    await app.emojis.add(message.from_user.id, name, doc_id, alt)
    await message.answer(app.localizer.get(locale, "emoji.saved", alt=alt, name=name), reply_markup=main_menu_keyboard(locale, is_admin=message.from_user.id in app.settings.admin_ids))


@router.message(F.chat.type == "private", F.entities)
async def direct_custom_emoji_message(message: Message, app, locale: str):
    pairs = await app.emojis.extract_pairs(message)
    if not pairs:
        return
    ids = "\n".join(f"`{did}`" for did, _ in pairs)
    await message.answer(f"{app.localizer.get(locale, 'emoji.detected', count=len(pairs))}\n\n{ids}")


@router.callback_query(F.data == "extract_pack")
async def extract_pack_start(callback: CallbackQuery, state: FSMContext, app, locale: str):
    await callback.answer()
    await state.set_state(ExtractFlow.waiting_pack_link)
    await callback.message.edit_text(app.localizer.get(locale, "extract.ask_pack"), reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 بازگشت" if locale == "fa" else "🔙 Back", callback_data=MenuCB(section="extract").pack())]]))


@router.message(ExtractFlow.waiting_pack_link)
async def extract_pack_message(message: Message, state: FSMContext, app, locale: str):
    text = (message.text or "").strip()
    match = PACK_LINK_RE.search(text)
    if not match:
        await message.answer(app.localizer.get(locale, "extract.invalid_pack"))
        return
    await state.clear()
    short_name = match.group(1)
    status = await message.answer(app.localizer.get(locale, "extract.loading"))
    try:
        docs = await app.bridge.fetch_pack_documents(short_name)
    except Exception as e:
        await status.edit_text(app.localizer.get(locale, "extract.error", error=str(e)))
        return
    if not docs:
        await status.edit_text(app.localizer.get(locale, "extract.empty"))
        return
    chunk = 40
    idx = 1
    for i in range(0, len(docs), chunk):
        text_chunk, entities, idx = app.emojis.build_pack_chunk(docs[i:i + chunk], idx)
        try:
            await app.bot.send_message(message.chat.id, text_chunk, entities=entities, parse_mode=None)
        except Exception as e:
            await message.answer(app.localizer.get(locale, "extract.chunk_error", error=str(e)))
        await asyncio.sleep(0.3)
    await status.edit_text(app.localizer.get(locale, "extract.done", count=len(docs), short_name=short_name))


@router.channel_post()
async def channel_post(message: Message, app, locale: str | None = None):
    if not message.chat or message.chat.type != "channel" or not message.text:
        return
    if not await app.channels.is_registered(message.chat.id):
        return
    await app.channels.auto_convert(app.bot, message.chat.id, message.message_id, message.text)


@router.callback_query(ChannelCB.filter())
async def channel_actions(callback: CallbackQuery, callback_data: ChannelCB, state: FSMContext, app, locale: str):
    await callback.answer()
    if callback_data.action == "add_start":
        await state.set_state(ChannelFlow.waiting_channel)
        await callback.message.edit_text(app.localizer.get(locale, "channels.ask_channel"), reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 بازگشت" if locale == "fa" else "🔙 Back", callback_data=MenuCB(section="channels").pack())]]))


@router.message(ChannelFlow.waiting_channel)
async def channel_input(message: Message, state: FSMContext, app, locale: str):
    await state.clear()
    raw = (message.text or "").strip()
    ok, title, channel_id = await app.channels.validate(app.bot, raw)
    if not ok:
        await message.answer(title or app.localizer.get(locale, "channels.invalid"))
        return
    saved = await app.channels.add(message.from_user.id, channel_id, title)
    if not saved:
        await message.answer(app.localizer.get(locale, "channels.duplicate"))
        return
    await message.answer(app.localizer.get(locale, "channels.saved", title=title or raw))


@router.callback_query(SupportCB.filter())
async def support_actions(callback: CallbackQuery, callback_data: SupportCB, state: FSMContext, app, locale: str):
    await callback.answer()
    if callback_data.action == "chat":
        await state.set_state(SupportFlow.waiting_support_message)
        await callback.message.edit_text(app.localizer.get(locale, "support.ask_chat"), reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 لغو" if locale == "fa" else "🔙 Cancel", callback_data=MenuCB(section="support").pack())]]))
    elif callback_data.action == "ticket":
        await state.set_state(SupportFlow.waiting_ticket_message)
        await callback.message.edit_text(app.localizer.get(locale, "support.ask_ticket"), reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 لغو" if locale == "fa" else "🔙 Cancel", callback_data=MenuCB(section="support").pack())]]))


@router.message(SupportFlow.waiting_support_message)
async def support_message_input(message: Message, state: FSMContext, app, locale: str):
    await state.clear()
    user = message.from_user
    for admin_id in app.settings.admin_ids:
        await app.bot.send_message(admin_id, app.localizer.get(locale, "support.admin_new_message", first_name=user.first_name or "", username=user.username or "-", user_id=user.id, message=message.text or ""))
    await message.answer(app.localizer.get(locale, "support.sent"))


@router.message(SupportFlow.waiting_ticket_message)
async def ticket_message_input(message: Message, state: FSMContext, app, locale: str):
    await state.clear()
    await app.support.add_ticket(message.from_user.id, message.text or "")
    user = message.from_user
    for admin_id in app.settings.admin_ids:
        await app.bot.send_message(admin_id, app.localizer.get(locale, "support.admin_new_ticket", first_name=user.first_name or "", username=user.username or "-", user_id=user.id, message=message.text or ""))
    await message.answer(app.localizer.get(locale, "support.ticket_saved"))


@router.message(Command("reply"))
async def admin_reply(message: Message, command: CommandObject, app, locale: str):
    if message.from_user.id not in app.settings.admin_ids:
        return
    args = (command.args or "").strip()
    parts = args.split(maxsplit=1)
    if len(parts) < 2 or not parts[0].isdigit():
        await message.answer(app.localizer.get(locale, "support.reply_usage"))
        return
    target_id = int(parts[0])
    body = parts[1]
    try:
        await app.bot.send_message(target_id, app.localizer.get(locale, "support.reply_message", message=body))
        await message.answer(app.localizer.get(locale, "support.reply_sent"))
    except Exception:
        await message.answer(app.localizer.get(locale, "support.reply_failed"))


@router.callback_query(AdminCB.filter())
async def admin_actions(callback: CallbackQuery, callback_data: AdminCB, state: FSMContext, app, locale: str):
    if callback.from_user.id not in app.settings.admin_ids:
        await callback.answer(app.localizer.get(locale, "admin.denied"), show_alert=True)
        return
    await callback.answer()
    action = callback_data.action
    if action == "panel":
        await show_admin_panel(callback.message, app, locale, edit=True)
    elif action == "stats":
        s = await app.admin.stats()
        await callback.message.edit_text(app.localizer.get(locale, "admin.stats", **s), reply_markup=admin_keyboard(locale))
    elif action == "unlimit":
        await state.set_state(AdminFlow.waiting_unlimit_target)
        await callback.message.edit_text(app.localizer.get(locale, "admin.ask_unlimit"), reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 لغو" if locale == "fa" else "🔙 Cancel", callback_data=AdminCB(action="panel").pack())]]))
    elif action == "broadcast":
        await state.set_state(AdminFlow.waiting_broadcast_message)
        await callback.message.edit_text(app.localizer.get(locale, "admin.ask_broadcast"), reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 لغو" if locale == "fa" else "🔙 Cancel", callback_data=AdminCB(action="panel").pack())]]))


@router.message(AdminFlow.waiting_unlimit_target)
async def unlimit_target_input(message: Message, state: FSMContext, app, locale: str):
    if message.from_user.id not in app.settings.admin_ids:
        return
    await state.clear()
    raw = (message.text or "").strip()
    if not raw.isdigit():
        await message.answer(app.localizer.get(locale, "admin.invalid_user_id"))
        return
    target_id = int(raw)
    await app.admin.unlimit(target_id)
    await message.answer(app.localizer.get(locale, "admin.unlimited", user_id=target_id))
    try:
        await app.bot.send_message(target_id, app.localizer.get(locale, "admin.user_unlimited"))
    except Exception:
        pass


@router.message(AdminFlow.waiting_broadcast_message)
async def broadcast_input(message: Message, state: FSMContext, app, locale: str):
    if message.from_user.id not in app.settings.admin_ids:
        return
    await state.clear()
    targets = await app.admin.broadcast_targets()
    status = await message.answer(app.localizer.get(locale, "admin.broadcasting", count=len(targets)))
    sent = 0
    failed = 0
    for uid in targets:
        try:
            await app.bot.send_message(uid, app.localizer.get(locale, "admin.broadcast_message", message=message.text or ""))
            sent += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)
    await status.edit_text(app.localizer.get(locale, "admin.broadcast_done", sent=sent, failed=failed))


@router.inline_query()
async def inline_query_handler(query: InlineQuery, app, locale: str | None = None):
    results = await app.inline.build_results(query.query)
    await query.answer(results=results, cache_time=0, is_personal=True)


@router.errors()
async def global_error_handler(event, app=None):
    logger.exception("Unhandled exception", exc_info=event.exception)
    return True
