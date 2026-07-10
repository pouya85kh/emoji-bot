import uuid

from aiogram import Router
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent,
)

from bot.telethon_client.premium import parse_query
from bot.utils.i18n import t

router = Router(name="inline")


def _edit_marker_keyboard() -> InlineKeyboardMarkup:
    """Telegram only reports msg_id in UpdateBotInlineSend (needed to edit
    the message after it's sent) when the sent inline result has an inline
    keyboard attached -- see https://core.telegram.org/api/bots/inline and
    Pyrogram's UpdateBotInlineSend docs ("Available only if there is an
    inline keyboard attached to the message"). Matches the original bot's
    exact trick: a button labeled with a zero-width non-joiner character
    (U+200C) so it's effectively invisible, with a throwaway callback_data,
    existing purely to satisfy that requirement."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="\u200c", callback_data="_")]
    ])


@router.inline_query()
async def on_inline_query(inline_query: InlineQuery, lang: str | None) -> None:
    """Answering the inline query itself never needs premium-emoji entities
    (Telegram doesn't render entities in the query-result preview), so this
    stays on Aiogram/Bot API. The premium-emoji rendering happens afterwards
    when the chosen result is actually sent, via the UpdateBotInlineSend raw
    event handled on the Telethon side (see main.py) -- which requires the
    reply_markup below to actually receive a usable msg_id."""
    query = inline_query.query.strip()

    if not query:
        example = "مثال: hi [5350291836378307462]" if lang != "en" else "example: hi [5350291836378307462]"
        results = [
            InlineQueryResultArticle(
                id=str(uuid.uuid4()),
                title=t(lang, "inline_default_title"),
                description=t(lang, "inline_default_desc"),
                input_message_content=InputTextMessageContent(message_text=example),
            )
        ]
        await inline_query.answer(results, cache_time=0, is_personal=True)
        return

    text, entities = parse_query(query)
    if not entities:
        results = [
            InlineQueryResultArticle(
                id=str(uuid.uuid4()),
                title=t(lang, "inline_bad_format_title"),
                description=t(lang, "inline_bad_format_desc"),
                input_message_content=InputTextMessageContent(message_text=t(lang, "inline_bad_format_text")),
            )
        ]
        await inline_query.answer(results, cache_time=0, is_personal=True)
        return

    preview = text[:50] + ("..." if len(text) > 50 else "")
    results = [
        InlineQueryResultArticle(
            id=str(uuid.uuid4()),
            title=t(lang, "inline_result_title", count=len(entities)),
            description=preview,
            input_message_content=InputTextMessageContent(message_text=query),
            reply_markup=_edit_marker_keyboard(),
        )
    ]
    await inline_query.answer(results, cache_time=0, is_personal=True)
