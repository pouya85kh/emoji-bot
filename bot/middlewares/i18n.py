from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from bot.database import database as db


class I18nMiddleware(BaseMiddleware):
    """Resolves the current user's language (falling back to the default in
    utils/i18n.t) and makes it available to handlers as data['lang']."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user is not None:
            data["lang"] = db.get_user_language(user.id)
        else:
            data["lang"] = None
        return await handler(event, data)
