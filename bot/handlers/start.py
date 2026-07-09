from aiogram import F, Router
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import CallbackQuery, Message

from bot.database import database as db
from bot.keyboards.inline import language_keyboard, main_menu_buttons
from bot.services import premium as premium_service
from bot.services import sharing as sharing_service
from bot.telethon_client.inline import send_deco, edit_deco_message
from bot.utils.i18n import t

router = Router(name="start")


async def send_main_menu(user_id: int, chat_id: int, first_name: str | None,
                          lang: str | None, edit_message_id: int | None = None) -> None:
    name = first_name or ("کاربر" if lang != "en" else "User")
    text = t(lang, "welcome", name=name)
    text, ent = premium_service.premiumize(text)
    # decorative rocket prefix entity, matching original send_main_menu()
    from telethon.tl import types
    from bot.config import EMOJI
    ent.append(types.MessageEntityCustomEmoji(offset=0, length=1, document_id=EMOJI["rocket"]))
    buttons = main_menu_buttons(lang, user_id)
    if edit_message_id:
        await edit_deco_message(chat_id, edit_message_id, text, ent, buttons)
    else:
        await send_deco(chat_id, text, ent, buttons)


@router.message(CommandStart(deep_link=True))
@router.message(CommandStart())
async def on_start(message: Message, command: CommandObject, lang: str | None) -> None:
    user = message.from_user
    db.ensure_user(user.id, user.first_name, user.username)

    stored_lang = db.get_user_language(user.id)
    if stored_lang is None:
        # Plain text, no premium-emoji entities needed here, but the keyboard
        # is still built with Telethon's Button so it renders identically to
        # every other menu -- sent through Telethon for consistency.
        await send_deco(message.chat.id, t(None, "choose_language"), None, language_keyboard())
        return

    arg = command.args
    if arg and arg.startswith("set_"):
        code = arg[len("set_"):]
        added = sharing_service.apply_shared_set(user.id, code)
        if added is None:
            await message.answer(t(stored_lang, "set_shared_invalid"))
        else:
            await message.answer(t(stored_lang, "set_shared_ok", added=added))
        return

    await send_main_menu(user.id, message.chat.id, user.first_name, stored_lang)


@router.callback_query(F.data == "lang_fa")
async def on_lang_fa(callback: CallbackQuery) -> None:
    db.set_user_language(callback.from_user.id, "fa")
    await callback.answer(t("fa", "language_saved"))
    await send_main_menu(callback.from_user.id, callback.message.chat.id,
                         callback.from_user.first_name, "fa",
                         edit_message_id=callback.message.message_id)


@router.callback_query(F.data == "lang_en")
async def on_lang_en(callback: CallbackQuery) -> None:
    db.set_user_language(callback.from_user.id, "en")
    await callback.answer(t("en", "language_saved"))
    await send_main_menu(callback.from_user.id, callback.message.chat.id,
                         callback.from_user.first_name, "en",
                         edit_message_id=callback.message.message_id)


@router.callback_query(F.data == "change_language")
async def on_change_language(callback: CallbackQuery) -> None:
    await callback.answer()
    await edit_deco_message(callback.message.chat.id, callback.message.message_id,
                             t(None, "choose_language"), None, language_keyboard())


@router.callback_query(F.data == "back_main")
async def on_back_main(callback: CallbackQuery, lang: str | None) -> None:
    await callback.answer()
    await send_main_menu(callback.from_user.id, callback.message.chat.id,
                         callback.from_user.first_name, lang,
                         edit_message_id=callback.message.message_id)


@router.callback_query(F.data == "noop")
async def on_noop(callback: CallbackQuery) -> None:
    await callback.answer()
