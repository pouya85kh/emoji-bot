from __future__ import annotations

import re
from typing import Sequence

from aiogram.types import Message, MessageEntity, Sticker

CODE_RE = re.compile(r"\[(\d+)\]")
PACK_LINK_RE = re.compile(r"(?:addemoji|addstickers)/([a-zA-Z0-9_]+)")

UNICODE_EMOJI_MAP: dict[str, str] = {
    "🚀": "rocket", "✈️": "telegram", "⭐": "star", "🔗": "link", "🖥": "panel",
    "❓": "help", "✉️": "mail", "💎": "gem", "⚡": "bolt", "📝": "note",
    "🎙": "mic", "🎁": "gift", "📊": "chart", "📋": "folder", "✅": "check",
    "⌘": "gear", "✏️": "pencil", "🦖": "dino", "🖼": "ticket", "🔙": "back",
    "📈": "rocket", "📨": "mail", "🔷": "bolt", "🎉": "gift", "📤": "link",
    "🅰": "note", "🔓": "check", "📢": "mail", "⏳": "bolt",
}


def utf16_len(text: str) -> int:
    return len(text.encode("utf-16-le")) // 2


def custom_emoji_entity(custom_emoji_id: int | str, offset: int, length: int = 1) -> MessageEntity:
    return MessageEntity(type="custom_emoji", offset=offset, length=length, custom_emoji_id=str(custom_emoji_id))


def premiumize(text: str, emoji_map: dict[str, int]) -> tuple[str, list[MessageEntity]]:
    entities: list[MessageEntity] = []
    out = ""
    i = 0
    while i < len(text):
        matched = False
        for ch, key in UNICODE_EMOJI_MAP.items():
            if text.startswith(ch, i) and key in emoji_map:
                offset = utf16_len(out)
                out += ch
                entities.append(custom_emoji_entity(emoji_map[key], offset=offset, length=utf16_len(ch)))
                i += len(ch)
                matched = True
                break
        if not matched:
            out += text[i]
            i += 1
    return out, entities


def extract_custom_emoji_pairs(message: Message) -> list[tuple[int, str]]:
    result: list[tuple[int, str]] = []
    if not message.text or not message.entities:
        return result
    raw_utf16 = message.text.encode("utf-16-le")
    for entity in message.entities:
        if entity.type == "custom_emoji" and entity.custom_emoji_id:
            start = entity.offset * 2
            end = start + entity.length * 2
            try:
                alt = raw_utf16[start:end].decode("utf-16-le")
            except Exception:
                alt = "⭐"
            result.append((int(entity.custom_emoji_id), alt or "⭐"))
    return result


def parse_codes(text: str | None) -> list[int]:
    return [int(m.group(1)) for m in CODE_RE.finditer(text or "")]


def parse_inline_query(query: str) -> tuple[str | None, list[MessageEntity] | None]:
    matches = list(CODE_RE.finditer(query))
    if not matches:
        return None, None
    out = ""
    entities: list[MessageEntity] = []
    last = 0
    for m in matches:
        out += query[last:m.start()]
        entities.append(custom_emoji_entity(int(m.group(1)), offset=utf16_len(out), length=1))
        out += "⭐"
        last = m.end()
    out += query[last:]
    return out.strip(), entities


def sticker_alt(sticker: Sticker, fallback: str = "⭐") -> str:
    return sticker.emoji or fallback


def build_pack_chunk(stickers: Sequence[Sticker], start_index: int, fallback: str = "⭐") -> tuple[str, list[MessageEntity], int]:
    text = ""
    entities: list[MessageEntity] = []
    idx = start_index
    for sticker in stickers:
        alt = sticker_alt(sticker, fallback)
        text += f"{idx}. "
        offset = utf16_len(text)
        entities.append(custom_emoji_entity(sticker.custom_emoji_id or 0, offset=offset, length=utf16_len(alt)))
        text += f"{alt}\n"
        id_str = f"[{sticker.custom_emoji_id}]"
        id_offset = utf16_len(text)
        text += id_str
        entities.append(MessageEntity(type="code", offset=id_offset, length=utf16_len(id_str)))
        text += "\n" + ("─" * 10) + "\n"
        idx += 1
    return text, entities, idx
