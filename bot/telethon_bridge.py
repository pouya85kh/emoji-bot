from __future__ import annotations

import asyncio
import logging

from telethon import events

from bot.utils import parse_inline_query

logger = logging.getLogger(__name__)


def register_telethon_inline_handler(client, bridge):
    @client.on(events.Raw)
    async def raw_handler(event):
        try:
            msg_id = getattr(event, "msg_id", None)
            if not msg_id:
                return
            query = (getattr(event, "query", "") or "").strip()
            text, entities = parse_inline_query(query)
            if not entities:
                return
            for attempt in range(3):
                try:
                    await asyncio.sleep(0.4 * (attempt + 1))
                    await bridge.edit_inline_message(msg_id, text, entities)
                    return
                except Exception as exc:
                    logger.warning("Inline edit failed (attempt %s): %s", attempt + 1, exc)
        except Exception:
            logger.exception("Telethon inline raw handler failed")
