"""
All outbound MTProto-only operations.

Design note (see main.py for full rationale): the shared Telethon client here
is used purely as an RPC client for calls the Bot API cannot make -- sending
or editing messages that carry MessageEntityCustomEmoji (premium emoji
requires MTProto for non-Premium bot accounts, see config docstring),
fetching sticker/emoji packs, checking channel admin permissions/member
counts, and editing already-sent inline messages. It does not independently
consume updates for business logic (Aiogram's Dispatcher does that) except
for the one raw event Bot API cannot deliver at all: UpdateBotInlineSend.
"""
from telethon.errors import ChatWriteForbiddenError, UserIsBlockedError
from telethon.tl import functions, types

from bot.telethon_client.client import client


async def send_deco(chat_id: int, text: str, entities: list | None = None, buttons=None):
    """Send a message whose entities may include premium emoji -- must go
    through Telethon, never Aiogram/Bot API (see module docstring)."""
    return await client.send_message(
        chat_id, text, formatting_entities=entities, buttons=buttons, parse_mode=None,
    )


async def edit_deco_message(chat_id: int, message_id: int, text: str,
                             entities: list | None = None, buttons=None):
    return await client.edit_message(
        chat_id, message_id, text, formatting_entities=entities, buttons=buttons, parse_mode=None,
    )


async def safe_send(user_id: int, text: str, entities: list | None = None, buttons=None) -> bool:
    try:
        await client.send_message(user_id, text, formatting_entities=entities,
                                   buttons=buttons, parse_mode=None)
        return True
    except (UserIsBlockedError, ChatWriteForbiddenError):
        return False
    except Exception:
        return False


async def fetch_pack_documents(short_name: str):
    result = await client(functions.messages.GetStickerSetRequest(
        stickerset=types.InputStickerSetShortName(short_name=short_name),
        hash=0,
    ))
    return result.documents


async def resolve_channel(identifier: str):
    """Resolve a channel by username or numeric id. Raises on failure."""
    return await client.get_entity(identifier)


async def get_channel_member_count(entity) -> int:
    full = await client(functions.channels.GetFullChannelRequest(entity))
    return full.full_chat.participants_count or 0


async def bot_has_edit_permission(entity) -> bool:
    me = await client.get_permissions(entity, "me")
    return bool(me.is_admin and getattr(me, "edit_messages", False))


async def get_bot_username() -> str:
    me = await client.get_me()
    return me.username


async def edit_inline_message(msg_id, text: str, entities: list) -> None:
    """Edit a message that was sent via inline mode. This requires the raw
    MTProto request + correct data-center routing; there is no Bot API
    equivalent for editing arbitrary inline-sent messages after the fact."""
    from telethon.tl.functions.messages import EditInlineBotMessageRequest
    request = EditInlineBotMessageRequest(id=msg_id, message=text, entities=entities)

    dc_id = msg_id.dc_id
    if dc_id == client.session.dc_id:
        await client(request)
    else:
        sender = await client._borrow_exported_sender(dc_id)
        try:
            await sender.send(request)
        finally:
            await client._return_exported_sender(sender)
