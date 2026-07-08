from __future__ import annotations

from aiogram.filters.callback_data import CallbackData


class LanguageCB(CallbackData, prefix="lang"):
    code: str
    next_action: str = "main"


class MenuCB(CallbackData, prefix="menu"):
    section: str


class EmojiPageCB(CallbackData, prefix="emoji_page"):
    page: int


class EmojiDeleteCB(CallbackData, prefix="emoji_del"):
    row_id: int


class EmojiActionCB(CallbackData, prefix="emoji_action"):
    action: str


class AccountCB(CallbackData, prefix="account"):
    action: str


class ChannelCB(CallbackData, prefix="channel"):
    action: str


class SupportCB(CallbackData, prefix="support"):
    action: str


class AdminCB(CallbackData, prefix="admin"):
    action: str


class MiscCB(CallbackData, prefix="misc"):
    action: str = "noop"
