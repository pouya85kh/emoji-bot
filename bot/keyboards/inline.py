"""
Inline keyboards.

Built with Telethon's Button helper, not Aiogram's InlineKeyboardBuilder,
because every decorated message in this bot must be sent/edited through the
Telethon client (premium-emoji entities require MTProto -- see
telethon_client/inline.py). Telethon's Button objects produce the exact same
callback_data-bearing keyboard on the wire, so Aiogram's Dispatcher still
receives and routes the resulting callback_query updates normally.
"""
from telethon import Button

from bot.config import config
from bot.utils.i18n import t


def language_keyboard():
    return [
        [Button.inline(t(None, "lang_fa_btn"), b"lang_fa"),
         Button.inline(t(None, "lang_en_btn"), b"lang_en")],
    ]


def main_menu_buttons(lang: str | None, user_id: int):
    rows = [
        [Button.inline(t(lang, "menu_premium_btn"), b"menu_premium"),
         Button.inline(t(lang, "menu_extract_btn"), b"menu_extract")],
        [Button.inline(t(lang, "menu_account_btn"), b"menu_account"),
         Button.inline(t(lang, "menu_help_btn"), b"menu_help")],
        [Button.inline(t(lang, "menu_support_btn"), b"menu_support")],
    ]
    if user_id in config.admin_ids:
        rows.append([Button.inline(t(lang, "admin_panel_btn"), b"admin_panel")])
    return rows


def back_button(lang: str | None, callback: str = "back_main"):
    return [[Button.inline(t(lang, "back_btn"), callback.encode())]]


def cancel_button(lang: str | None, callback: str):
    return [[Button.inline(t(lang, "cancel_btn"), callback.encode())]]


def premium_menu_buttons(lang: str | None):
    return [
        [Button.switch_inline(t(lang, "go_inline_btn"), query="", same_peer=False)],
        [Button.inline(t(lang, "back_btn"), b"back_main")],
    ]


def extract_menu_buttons(lang: str | None):
    return [
        [Button.inline(t(lang, "extract_pack_btn"), b"extract_pack")],
        [Button.inline(t(lang, "back_btn"), b"back_main")],
    ]


def my_emojis_buttons(lang: str | None, page_rows, page: int, total_pages: int):
    buttons = []
    for r in page_rows:
        alt = r.alt if r.alt else None
        label = f"{alt} {r.name}" if alt else r.name
        buttons.append([
            Button.inline(label, b"noop"),
            Button.inline(t(lang, "delete_btn"), f"del_emoji_{r.id}".encode()),
        ])
    nav_row = [
        Button.inline(f"{page + 1}/{total_pages}", b"noop"),
        Button.inline(t(lang, "next_btn"), f"myemo_page_{page + 1}".encode()),
    ]
    buttons.append(nav_row)
    buttons.append([Button.inline(t(lang, "add_emoji_btn"), b"add_emoji_start")])
    buttons.append([Button.inline(t(lang, "back_btn"), b"menu_account")])
    return buttons


def account_menu_buttons(lang: str | None):
    return [
        [Button.inline(t(lang, "my_emojis_btn"), b"menu_my_emojis"),
         Button.inline(t(lang, "my_stats_btn"), b"my_stats")],
        [Button.inline(t(lang, "my_channels_btn"), b"menu_channels"),
         Button.inline(t(lang, "my_set_btn"), b"my_set")],
        [Button.inline(t(lang, "change_language_btn"), b"change_language")],
        [Button.inline(t(lang, "back_btn"), b"back_main")],
    ]


def my_set_buttons(lang: str | None, code: str):
    return [
        [Button.inline(t(lang, "copy_link_btn"), f"copy_set_{code}".encode())],
        [Button.inline(t(lang, "back_btn"), b"menu_account")],
    ]


def channels_menu_buttons(lang: str | None):
    return [
        [Button.inline(t(lang, "add_channel_btn"), b"add_channel_start")],
        [Button.inline(t(lang, "back_btn"), b"menu_account")],
    ]


def support_menu_buttons(lang: str | None):
    return [
        [Button.inline(t(lang, "support_chat_btn"), b"support_chat"),
         Button.inline(t(lang, "support_ticket_btn"), b"support_ticket")],
        [Button.inline(t(lang, "back_btn"), b"back_main")],
    ]


def admin_panel_buttons(lang: str | None):
    return [
        [Button.inline(t(lang, "admin_stats_btn"), b"admin_stats")],
        [Button.inline(t(lang, "admin_unlimit_btn"), b"admin_unlimit")],
        [Button.inline(t(lang, "admin_broadcast_btn"), b"admin_broadcast")],
        [Button.inline(t(lang, "back_btn"), b"back_main")],
    ]
