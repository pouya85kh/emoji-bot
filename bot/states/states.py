from aiogram.fsm.state import State, StatesGroup


class LanguageStates(StatesGroup):
    choosing = State()


class SupportStates(StatesGroup):
    """Replaces pending action 'await_support_msg'."""
    awaiting_message = State()


class TicketStates(StatesGroup):
    """Replaces pending action 'await_ticket_msg'."""
    awaiting_message = State()


class AdminUnlimitStates(StatesGroup):
    """Replaces pending action 'await_unlimit_target'."""
    awaiting_target_id = State()


class AdminBroadcastStates(StatesGroup):
    """Replaces pending action 'await_broadcast_msg'."""
    awaiting_message = State()


class ExtractPackStates(StatesGroup):
    """Replaces pending action 'await_pack_link'."""
    awaiting_link = State()


class AddEmojiStates(StatesGroup):
    """Replaces pending actions 'await_add_emoji_id' / 'await_add_emoji_name'."""
    awaiting_emoji = State()
    awaiting_name = State()


class AddChannelStates(StatesGroup):
    """Replaces pending action 'await_channel_id'."""
    awaiting_channel = State()
