from aiogram import F, Router
from aiogram.types import CallbackQuery

from bot.keyboards.inline import premium_menu_buttons
from bot.telethon_client.inline import edit_deco_message
from bot.utils.i18n import t

router = Router(name="premium")


@router.callback_query(F.data == "menu_premium")
async def on_menu_premium(callback: CallbackQuery, lang: str | None) -> None:
    await callback.answer()
    text = t(lang, "premium_intro")
    await edit_deco_message(callback.message.chat.id, callback.message.message_id, text, None,
                             premium_menu_buttons(lang))
