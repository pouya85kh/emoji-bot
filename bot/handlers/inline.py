import uuid

from aiogram import Router
from aiogram.types import InlineQuery, InlineQueryResultArticle, InputTextMessageContent

from bot.telethon_client.premium import parse_query
from bot.utils.i18n import t

router = Router(name="inline")


@router.inline_query()
async def on_inline_query(inline_query: InlineQuery, lang: str | None) -> None:
    """Answering the inline query itself never needs premium-emoji entities
    (Telegram doesn't render entities in the query-result preview), so this
    stays on Aiogram/Bot API. The premium-emoji rendering happens afterwards
    when the chosen result is actually sent, via the UpdateBotInlineSend raw
    event handled on the Telethon side (see main.py)."""
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
        )
    ]
    await inline_query.answer(results, cache_time=0, is_personal=True)
