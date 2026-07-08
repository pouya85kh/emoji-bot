from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import Bot
from aiogram.dispatcher.middlewares.base import BaseMiddleware
from aiogram.types import CallbackQuery, Message

from bot.keyboards import language_keyboard


class AppContextMiddleware(BaseMiddleware):
    def __init__(self, app) -> None:
        super().__init__()
        self.app = app

    async def __call__(self, handler: Callable[[Any, dict[str, Any]], Awaitable[Any]], event: Any, data: dict[str, Any]) -> Any:
        data["app"] = self.app
        data["bot"] = self.app.bot
        data["db"] = self.app.db
        data["settings"] = self.app.settings
        data["localizer"] = self.app.localizer
        return await handler(event, data)


class LocaleGuardMiddleware(BaseMiddleware):
    async def __call__(self, handler: Callable[[Any, dict[str, Any]], Awaitable[Any]], event: Any, data: dict[str, Any]) -> Any:
        app = data["app"]
        user = getattr(event, "from_user", None)
        if user is None:
            return await handler(event, data)

        locale = await app.db.get_locale(user.id)
        data["locale"] = locale
        data["t"] = lambda key, **kwargs: app.localizer.get(locale, key, **kwargs)

        if locale is not None:
            return await handler(event, data)

        is_start = isinstance(event, Message) and (event.text or "").startswith("/start")
        is_lang = isinstance(event, CallbackQuery) and bool(event.data and event.data.startswith(b"lang:"))
        if is_start or is_lang:
            return await handler(event, data)

        text = "Choose your language / زبان را انتخاب کنید"
        if isinstance(event, CallbackQuery) and event.message:
            try:
                await event.answer()
                await event.message.edit_text(text, reply_markup=language_keyboard("start"))
            except Exception:
                await event.answer(text, show_alert=True)
        elif isinstance(event, Message):
            await event.answer(text, reply_markup=language_keyboard("start"))
        return None
