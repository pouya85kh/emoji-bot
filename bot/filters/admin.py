from aiogram.filters import BaseFilter
from aiogram.types import TelegramObject

from bot.config import config


class IsAdmin(BaseFilter):
    async def __call__(self, event: TelegramObject, event_from_user=None, **kwargs) -> bool:
        user = event_from_user or getattr(event, "from_user", None)
        return bool(user and user.id in config.admin_ids)
