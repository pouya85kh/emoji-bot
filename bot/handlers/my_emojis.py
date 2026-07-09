from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from telethon import Button
from telethon.tl import types

from bot.config import config
from bot.database import database as db
from bot.keyboards.inline import cancel_button, my_emojis_buttons
from bot.services import premium as premium_service
from bot.states.states import AddEmojiStates
from bot.telethon_client.inline import edit_deco_message, send_deco
from bot.utils.entities import extract_ids_with_alt, parse_codes_from_text
from bot.utils.i18n import t

router = Router(name="my_emojis")


async def _render_and_edit(callback: CallbackQuery, lang: str | None, page: int) -> None:
    result = premium_service.render_my_emojis_page(lang, callback.from_user.id, page)
    buttons = my_emojis_buttons(lang, result.rows, result.page, result.total_pages)
    await edit_deco_message(callback.message.chat.id, callback.message.message_id,
                             result.text, result.entities, buttons)


@router.callback_query(F.data == "menu_my_emojis")
async def on_my_emojis(callback: CallbackQuery, lang: str | None) -> None:
    await callback.answer()
    await _render_and_edit(callback, lang, 0)


@router.callback_query(F.data.startswith("myemo_page_"))
async def on_my_emojis_page(callback: CallbackQuery, lang: str | None) -> None:
    await callback.answer()
    page = int(callback.data[len("myemo_page_"):])
    await _render_and_edit(callback, lang, page)


@router.callback_query(F.data.startswith("del_emoji_"))
async def on_del_emoji(callback: CallbackQuery, lang: str | None) -> None:
    row_id = int(callback.data[len("del_emoji_"):])
    premium_service.delete_emoji(row_id, callback.from_user.id)
    await callback.answer(t(lang, "deleted"))
    await _render_and_edit(callback, lang, 0)


@router.callback_query(F.data == "add_emoji_start")
async def on_add_emoji_start(callback: CallbackQuery, state: FSMContext, lang: str | None) -> None:
    limit = db.user_limit(callback.from_user.id)
    if limit is not None and db.user_emoji_count(callback.from_user.id) >= limit:
        await callback.answer(t(lang, "limit_reached", limit=limit), show_alert=True)
        return
    await callback.answer()
    await state.set_state(AddEmojiStates.awaiting_emoji)
    await edit_deco_message(callback.message.chat.id, callback.message.message_id,
                             t(lang, "add_emoji_prompt"), None,
                             cancel_button(lang, callback="menu_my_emojis"))


@router.message(StateFilter(AddEmojiStates.awaiting_emoji), F.chat.type == "private")
async def on_add_emoji_id_input(message: Message, state: FSMContext, lang: str | None) -> None:
    pairs = extract_ids_with_alt(message)
    if not pairs:
        codes = parse_codes_from_text(message.text or "")
        pairs = [(c, config.fallback_emoji) for c in codes]
    if not pairs:
        await message.reply(t(lang, "add_emoji_not_found"))
        return

    doc_id, alt = pairs[0]
    # Only move to the "awaiting name" state here; nothing is saved to the
    # database until the name is actually provided in the next message.
    await state.update_data(doc_id=doc_id, alt=alt)
    await state.set_state(AddEmojiStates.awaiting_name)

    ent = [types.MessageEntityCustomEmoji(offset=0, length=premium_service.utf16_len(alt), document_id=doc_id)]
    await send_deco(message.chat.id, t(lang, "add_emoji_ask_name", alt=alt), ent)


@router.message(StateFilter(AddEmojiStates.awaiting_name), F.chat.type == "private")
async def on_add_emoji_name_input(message: Message, state: FSMContext, lang: str | None) -> None:
    data = await state.get_data()
    await state.clear()
    doc_id = data["doc_id"]
    alt = data.get("alt", config.fallback_emoji)
    name = (message.text or "").strip()
    if not name or premium_service.is_default_name_word(lang, name):
        name = premium_service.default_emoji_name(lang, doc_id)

    limit = db.user_limit(message.from_user.id)
    if limit is not None and db.user_emoji_count(message.from_user.id) >= limit:
        await message.reply(t(lang, "limit_reached_plain", limit=limit))
        return

    premium_service.save_emoji(message.from_user.id, name, doc_id, alt)

    ent = [types.MessageEntityCustomEmoji(offset=0, length=premium_service.utf16_len(alt), document_id=doc_id)]
    await send_deco(message.chat.id, t(lang, "add_emoji_saved", alt=alt, name=name), ent,
                     [[Button.inline(t(lang, "my_emojis_btn"), b"menu_my_emojis")]])
