"""
Channel service: registration validation (member count + bot admin/edit
permission checks, both MTProto-only) and the auto-convert logic applied to
channel posts containing [id] codes.
"""
from bot.config import CODE_RE, config
from bot.database import database as db
from bot.telethon_client import inline as tl_inline
from bot.telethon_client import premium as premium_tl


class ChannelError(Exception):
    """Raised with an i18n key + kwargs for the handler to render."""

    def __init__(self, key: str, **kwargs):
        self.key = key
        self.kwargs = kwargs
        super().__init__(key)


async def register_channel(user_id: int, identifier: str):
    from telethon.tl import types

    try:
        entity = await tl_inline.resolve_channel(identifier)
    except Exception as e:
        raise ChannelError("channel_not_found", error=str(e))

    if not isinstance(entity, types.Channel):
        raise ChannelError("channel_invalid")

    try:
        members_count = await tl_inline.get_channel_member_count(entity)
    except Exception:
        members_count = 0

    if members_count and members_count < config.channel_min_members:
        raise ChannelError("channel_too_small", min_members=config.channel_min_members,
                            count=members_count)

    try:
        has_perm = await tl_inline.bot_has_edit_permission(entity)
    except Exception as e:
        raise ChannelError("channel_perm_check_failed", error=str(e))

    if not has_perm:
        raise ChannelError("channel_no_admin")

    ok = db.add_channel(user_id, entity.id, entity.title)
    if not ok:
        raise ChannelError("channel_already_registered")

    return entity


def is_registered_channel(channel_id) -> bool:
    return db.is_registered_channel(channel_id) is not None


def has_emoji_code(text: str) -> bool:
    return bool(text and CODE_RE.search(text))


async def auto_convert_post(chat, message_id: int, raw_text: str) -> None:
    """Rewrite a channel post's [id] codes into real premium-emoji entities.
    Only Telethon can perform this edit (formatting_entities on an
    already-posted channel message with custom emoji)."""
    text, entities = premium_tl.parse_query(raw_text)
    if not entities:
        return
    try:
        await tl_inline.edit_deco_message(chat.id, message_id, text, entities)
    except Exception as e:
        print(f"channel auto-convert failed: {e}")
