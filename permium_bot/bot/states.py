from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class StartFlow(StatesGroup):
    waiting_language = State()


class EmojiFlow(StatesGroup):
    waiting_emoji_id = State()
    waiting_emoji_name = State()


class ExtractFlow(StatesGroup):
    waiting_pack_link = State()


class ChannelFlow(StatesGroup):
    waiting_channel = State()


class SupportFlow(StatesGroup):
    waiting_support_message = State()
    waiting_ticket_message = State()


class AdminFlow(StatesGroup):
    waiting_unlimit_target = State()
    waiting_broadcast_message = State()
