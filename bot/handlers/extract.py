import asyncio

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.keyboards.inline import back_button, extract_menu_buttons
from bot.services import extractor as extractor_service
from bot.states.states import ExtractPackStates
from bot.telethon_client.inline import edit_deco_message, send_deco
from bot.utils.entities import extract_ids
from bot.utils.i18n import t

router = Router(name="extract")


@router.callback_query(F.data == "menu_extract")
async def on_menu_extract(callback: CallbackQuery, state: FSMContext, lang: str | None) -> None:
    await callback.answer()
    await state.clear()
    text = t(lang, "extract_intro")
    await edit_deco_message(callback.message.chat.id, callback.message.message_id, text, None,
                             extract_menu_buttons(lang))


@router.callback_query(F.data == "extract_pack")
async def on_extract_pack(callback: CallbackQuery, state: FSMContext, lang: str | None) -> None:
    await callback.answer()
    await state.set_state(ExtractPackStates.awaiting_link)
    await edit_deco_message(callback.message.chat.id, callback.message.message_id,
                             t(lang, "extract_pack_prompt"), None,
                             back_button(lang, callback="menu_extract"))


@router.message(StateFilter(ExtractPackStates.awaiting_link), F.chat.type == "private")
async def on_pack_link_input(message: Message, state: FSMContext, lang: str | None) -> None:
    short_name = extractor_service.match_pack_link(message.text or "")
    if not short_name:
        await message.reply(t(lang, "extract_pack_invalid"))
        return
    await state.clear()

    status = await message.reply(t(lang, "extract_pack_fetching"))
    try:
        docs = await extractor_service.fetch_pack_documents(short_name)
    except Exception as e:
        await status.edit_text(t(lang, "extract_pack_error", error=str(e)))
        return

    if not docs:
        await status.edit_text(t(lang, "extract_pack_empty"))
        return

    idx = 1
    for chunk_docs in extractor_service.chunk_documents(docs):
        text, entities, idx = extractor_service.build_numbered_chunk(chunk_docs, idx)
        try:
            await send_deco(message.chat.id, text, entities)
        except Exception as e:
            await message.reply(t(lang, "extract_pack_partial_error", error=str(e)))
        await asyncio.sleep(0.3)

    await status.edit_text(t(lang, "extract_pack_done", count=len(docs), name=short_name))


@router.message(StateFilter(None), F.chat.type == "private", F.entities)
async def on_direct_emoji_message(message: Message, lang: str | None) -> None:
    doc_ids = extract_ids(message)
    if not doc_ids:
        return
    text = t(lang, "extract_direct_detected", count=len(doc_ids))
    for did in doc_ids:
        text += f"`{did}`\n"
    # Telethon's client defaults to markdown parsing, so the backticks in the
    # original rendered as code spans; explicitly request Markdown here to
    # preserve that (the rest of the bot's aiogram traffic defaults to no
    # parse mode -- see loader.py).
    await message.reply(text, parse_mode="Markdown")
