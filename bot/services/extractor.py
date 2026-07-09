"""
Extraction service: pack-link extraction and direct-message premium-emoji
detection. No limits are applied here, matching the original bot exactly.
"""
from bot.config import PACK_LINK_RE
from bot.telethon_client import inline as tl_inline
from bot.telethon_client import premium as premium_tl

CHUNK_SIZE = 40


def match_pack_link(text: str) -> str | None:
    match = PACK_LINK_RE.search(text or "")
    return match.group(1) if match else None


async def fetch_pack_documents(short_name: str):
    return await tl_inline.fetch_pack_documents(short_name)


def chunk_documents(docs, chunk_size: int = CHUNK_SIZE):
    for i in range(0, len(docs), chunk_size):
        yield docs[i:i + chunk_size]


def build_numbered_chunk(docs, start_index: int = 1):
    return premium_tl.build_numbered_chunk(docs, start_index)


def detect_direct_emojis(entities: list | None) -> list[int]:
    return premium_tl.extract_entities_from_message(entities)
