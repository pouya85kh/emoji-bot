from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.config import config
from bot.database import database as db
from bot.keyboards.inline import back_button, channels_menu_buttons
from bot.services import channels as channels_service
from bot.services import premium as premium_service
from bot.states.states import AddChannelStates
from bot.telethon_client.inline import edit_deco_message
from bot.utils.i18n import t

router = Router(name="channels")


@router.callback_query(F.data == "menu_channels")
async def on_menu_channels(callback: CallbackQuery, lang: str | None) -> None:
    await callback.answer()
    chans = db.list_channels(callback.from_user.id)
    text = t(lang, "channels_header")
    if not chans:
        text += t(lang, "channels_empty")
    else:
        text += "\n" + "\n".join(f"◁ {c['title'] or c['channel_id']}" for c in chans)

    text, ent = premium_service.premiumize(text)
    await edit_deco_message(callback.message.chat.id, callback.message.message_id, text, ent,
                             channels_menu_buttons(lang))


@router.callback_query(F.data == "add_channel_start")
async def on_add_channel_start(callback: CallbackQuery, state: FSMContext, lang: str | None) -> None:
    await callback.answer()
    await state.set_state(AddChannelStates.awaiting_channel)
    text = t(lang, "add_channel_prompt", min_members=config.channel_min_members)
    text, ent = premium_service.premiumize(text)
    await edit_deco_message(callback.message.chat.id, callback.message.message_id, text, ent,
                             back_button(lang, callback="menu_channels"))


@router.message(StateFilter(AddChannelStates.awaiting_channel), F.chat.type == "private")
async def on_channel_id_input(message: Message, state: FSMContext, lang: str | None) -> None:
    await state.clear()
    raw = (message.text or "").strip()
    try:
        entity = await channels_service.register_channel(message.from_user.id, raw)
    except channels_service.ChannelError as e:
        await message.reply(t(lang, e.key, **e.kwargs))
        return

    await message.reply(t(lang, "channel_added", title=entity.title))


@router.channel_post(F.text.func(lambda text: channels_service.has_emoji_code(text)) |
                      F.caption.func(lambda caption: channels_service.has_emoji_code(caption)))
async def on_channel_post(message: Message) -> None:
    if not channels_service.is_registered_channel(message.chat.id):
        return
    raw_text = message.text or message.caption or ""
    await channels_service.auto_convert_post(message.chat, message.message_id, raw_text)
