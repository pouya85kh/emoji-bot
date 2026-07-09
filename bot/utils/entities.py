from aiogram.types import Message, MessageEntity

from bot.config import config


def custom_emoji_entities(message: Message) -> list[MessageEntity]:
    entities = message.entities or message.caption_entities or []
    return [e for e in entities if e.type == "custom_emoji"]


def extract_ids(message: Message) -> list[int]:
    return [int(e.custom_emoji_id) for e in custom_emoji_entities(message)]


def extract_ids_with_alt(message: Message) -> list[tuple[int, str]]:
    text = message.text or message.caption or ""
    text16 = text.encode("utf-16-le")
    result = []
    for e in custom_emoji_entities(message):
        start = e.offset * 2
        end = start + e.length * 2
        try:
            alt = text16[start:end].decode("utf-16-le")
        except Exception:
            alt = config.fallback_emoji
        result.append((int(e.custom_emoji_id), alt or config.fallback_emoji))
    return result


def parse_codes_from_text(text: str) -> list[int]:
    from bot.config import CODE_RE
    return [int(m.group(1)) for m in CODE_RE.finditer(text or "")]
