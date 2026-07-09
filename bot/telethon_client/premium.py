"""
Premium custom-emoji entity handling.

This is the most critical part of the migration: MessageEntityCustomEmoji
construction/extraction is MTProto-only and has no Bot API equivalent, so all
of this stays on Telethon exactly as in the original bot. Do not change this
logic.
"""
import re

from telethon.tl import types

from bot.config import EMOJI, UNICODE_EMOJI_MAP, config

CODE_RE = re.compile(r"\[(\d+)\]")


def utf16_len(text: str) -> int:
    return len(text.encode("utf-16-le")) // 2


def doc_alt(doc) -> str:
    for attr in doc.attributes:
        if isinstance(attr, types.DocumentAttributeCustomEmoji):
            return attr.alt or config.fallback_emoji
    return config.fallback_emoji


def extract_entities_from_message(entities: list | None) -> list[int]:
    """Return the document_ids of any real premium-emoji entities present on
    a message (i.e. the user actually sent a premium emoji, not text)."""
    ids = []
    if entities:
        for e in entities:
            if isinstance(e, types.MessageEntityCustomEmoji):
                ids.append(e.document_id)
    return ids


def extract_emojis_with_alt(raw_text: str | None, entities: list | None) -> list[tuple[int, str]]:
    """For each real premium-emoji entity on the message, return
    (document_id, alt_glyph) -- alt is the actual glyph rendered under the
    entity, needed so it can be redisplayed later (e.g. in "My Emojis")."""
    result = []
    if entities and raw_text:
        text16 = raw_text.encode("utf-16-le")
        for e in entities:
            if isinstance(e, types.MessageEntityCustomEmoji):
                start = e.offset * 2
                end = start + e.length * 2
                try:
                    alt = text16[start:end].decode("utf-16-le")
                except Exception:
                    alt = config.fallback_emoji
                result.append((e.document_id, alt or config.fallback_emoji))
    return result


def parse_codes_from_text(text: str) -> list[int]:
    return [int(m.group(1)) for m in CODE_RE.finditer(text)]


def premiumize(text: str) -> tuple[str, list]:
    """Overlay a MessageEntityCustomEmoji on every known plain unicode emoji
    in `text`, without changing the visible text -- makes decorative emojis
    render as premium in clients that support it. Output: (unchanged text,
    entities list).

    No-op (returns the text unchanged with no entities) unless
    config.enable_decorative_emoji is True, since doing this for real
    requires a genuine premium-emoji document id in config.deco_emoji_id --
    see config.py."""
    if not config.enable_decorative_emoji:
        return text, []

    entities = []
    out = ""
    i = 0
    n = len(text)
    while i < n:
        matched = False
        for ch, key in UNICODE_EMOJI_MAP.items():
            if text.startswith(ch, i):
                offset = utf16_len(out)
                out += ch
                entities.append(types.MessageEntityCustomEmoji(
                    offset=offset, length=utf16_len(ch), document_id=EMOJI[key],
                ))
                i += len(ch)
                matched = True
                break
        if not matched:
            out += text[i]
            i += 1
    return out, entities


def with_deco(key: str, text: str) -> tuple[str, list]:
    """Text with a single decorative premium emoji prefixed, plus its entity.
    Falls back to a plain fallback-glyph prefix (no entity) until a real
    decorative emoji id is configured -- see config.enable_decorative_emoji."""
    full_text = config.fallback_emoji + "  " + text
    if not config.enable_decorative_emoji:
        return full_text, []
    ent = types.MessageEntityCustomEmoji(offset=0, length=1, document_id=EMOJI[key])
    return full_text, [ent]


def build_numbered_chunk(docs, start_index: int = 1) -> tuple[str, list, int]:
    """Render a numbered list of pack documents with real premium-emoji
    entities plus a copyable code entity, exactly as the original pack
    extraction output."""
    text = ""
    entities = []
    idx = start_index
    for doc in docs:
        alt = doc_alt(doc)
        prefix = f"{idx}. "
        text += prefix
        emoji_offset = utf16_len(text)
        entities.append(types.MessageEntityCustomEmoji(
            offset=emoji_offset, length=utf16_len(alt), document_id=doc.id,
        ))
        text += alt + "\n"
        id_str = f"[{doc.id}]"
        id_offset = utf16_len(text)
        text += id_str
        entities.append(types.MessageEntityCode(offset=id_offset, length=utf16_len(id_str)))
        text += "\n" + ("─" * 10) + "\n"
        idx += 1
    return text, entities, idx


def parse_query(query: str) -> tuple[str | None, list | None]:
    """Parse an inline-query string containing [docid] codes into
    (display_text, entities) for premium emoji rendering."""
    matches = list(CODE_RE.finditer(query))
    if not matches:
        return None, None

    text = ""
    entities = []
    last = 0
    for m in matches:
        text += query[last:m.start()]
        entities.append(types.MessageEntityCustomEmoji(
            offset=utf16_len(text),
            length=1,
            document_id=int(m.group(1)),
        ))
        text += config.fallback_emoji
        last = m.end()

    text += query[last:]
    return text.strip(), entities
