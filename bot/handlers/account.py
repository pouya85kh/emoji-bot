from aiogram import F, Router
from aiogram.types import CallbackQuery

from bot.database import database as db
from bot.keyboards.inline import account_menu_buttons, back_button, my_set_buttons
from bot.services import premium as premium_service
from bot.services import sharing as sharing_service
from bot.telethon_client.inline import edit_deco_message
from bot.utils.i18n import t

router = Router(name="account")


@router.callback_query(F.data == "menu_account")
async def on_menu_account(callback: CallbackQuery, lang: str | None) -> None:
    await callback.answer()
    user = callback.from_user
    db.ensure_user(user.id, user.first_name, user.username)
    u = db.get_user(user.id)
    limit = db.user_limit(user.id)
    limit_txt = t(lang, "unlimited") if limit is None else str(limit)
    count = db.user_emoji_count(user.id)
    kind = t(lang, "kind_unlimited") if u["unlimited"] else t(lang, "kind_normal")

    text = t(lang, "account_header", user_id=user.id, first_name=user.first_name or "-",
              username=user.username or "-", kind=kind, count=count, limit=limit_txt)
    text, ent = premium_service.premiumize(text)
    await edit_deco_message(callback.message.chat.id, callback.message.message_id,
                             text, ent, account_menu_buttons(lang))


@router.callback_query(F.data == "my_stats")
async def on_my_stats(callback: CallbackQuery, lang: str | None) -> None:
    await callback.answer()
    count = db.user_emoji_count(callback.from_user.id)
    channels = len(db.list_channels(callback.from_user.id))
    text = t(lang, "my_stats_text", count=count, channels=channels)
    text, ent = premium_service.premiumize(text)
    await edit_deco_message(callback.message.chat.id, callback.message.message_id, text, ent,
                             back_button(lang, callback="menu_account"))


@router.callback_query(F.data == "my_set")
async def on_my_set(callback: CallbackQuery, lang: str | None) -> None:
    await callback.answer()
    code = sharing_service.get_or_create_set_code(callback.from_user.id)
    count = db.user_emoji_count(callback.from_user.id)
    link = await sharing_service.build_set_link(code)
    text = t(lang, "my_set_text", count=count, code=code, link=link)
    text, ent = premium_service.premiumize(text)
    await edit_deco_message(callback.message.chat.id, callback.message.message_id, text, ent,
                             my_set_buttons(lang, code))


@router.callback_query(F.data.startswith("copy_set_"))
async def on_copy_set(callback: CallbackQuery, lang: str | None) -> None:
    code = callback.data[len("copy_set_"):]
    link = await sharing_service.build_set_link(code)
    await callback.answer(t(lang, "copy_link_alert", link=link), show_alert=True)
