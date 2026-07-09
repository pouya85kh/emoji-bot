from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import config
from bot.middlewares.error import ErrorHandlingMiddleware
from bot.middlewares.i18n import I18nMiddleware

bot = Bot(token=config.bot_token, default=DefaultBotProperties(parse_mode=None))
dp = Dispatcher(storage=MemoryStorage())

dp.update.outer_middleware(ErrorHandlingMiddleware())
dp.update.outer_middleware(I18nMiddleware())
