from __future__ import annotations

from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.callbacks import AccountCB, AdminCB, ChannelCB, EmojiActionCB, EmojiDeleteCB, EmojiPageCB, LanguageCB, MenuCB, MiscCB, SupportCB


def language_keyboard(next_action: str = "main"):
    b = InlineKeyboardBuilder()
    b.button(text="🇮🇷 فارسی", callback_data=LanguageCB(code="fa", next_action=next_action).pack())
    b.button(text="🇺🇸 English", callback_data=LanguageCB(code="en", next_action=next_action).pack())
    b.adjust(2)
    return b.as_markup()


def main_menu_keyboard(locale: str, is_admin: bool = False):
    b = InlineKeyboardBuilder()
    b.button(text="⭐ ایموجی پریمیوم" if locale == "fa" else "⭐ Premium Emoji", callback_data=MenuCB(section="premium").pack())
    b.button(text="🔗 استخراج کد ایموجی" if locale == "fa" else "🔗 Extract Emoji ID", callback_data=MenuCB(section="extract").pack())
    b.button(text="🖥 حساب من" if locale == "fa" else "🖥 My Profile", callback_data=MenuCB(section="account").pack())
    b.button(text="❓ راهنما" if locale == "fa" else "❓ Help", callback_data=MenuCB(section="help").pack())
    b.button(text="✉️ پشتیبانی" if locale == "fa" else "✉️ Support", callback_data=MenuCB(section="support").pack())
    if is_admin:
        b.button(text="⚙️ پنل مدیریت" if locale == "fa" else "⚙️ Admin Panel", callback_data=AdminCB(action="panel").pack())
    b.adjust(2, 2, 1, 1)
    return b.as_markup()


def account_keyboard(locale: str):
    b = InlineKeyboardBuilder()
    b.button(text="⭐ ایموجی‌های من" if locale == "fa" else "⭐ My Emojis", callback_data=MenuCB(section="my_emojis").pack())
    b.button(text="📊 آمار من" if locale == "fa" else "📊 My Stats", callback_data=AccountCB(action="stats").pack())
    b.button(text="📋 کانال‌های من" if locale == "fa" else "📋 My Channels", callback_data=MenuCB(section="channels").pack())
    b.button(text="⭐ اشتراک ست من" if locale == "fa" else "⭐ My Set Link", callback_data=AccountCB(action="set").pack())
    b.button(text="🌐 تغییر زبان" if locale == "fa" else "🌐 Change Language", callback_data=AccountCB(action="change_lang").pack())
    b.button(text="🔙 بازگشت" if locale == "fa" else "🔙 Back", callback_data=MenuCB(section="main").pack())
    b.adjust(2, 2, 1, 1)
    return b.as_markup()


def emojis_keyboard(locale: str, page: int, total_pages: int, page_rows):
    b = InlineKeyboardBuilder()
    for row in page_rows:
        alt = row.alt or "⭐"
        b.button(text=f"{alt} {row.name}", callback_data=MiscCB(action="noop").pack())
        b.button(text="🗑 حذف" if locale == "fa" else "🗑 Delete", callback_data=EmojiDeleteCB(row_id=row.id).pack())
    b.button(text=f"{page + 1}/{total_pages}", callback_data=MiscCB(action="noop").pack())
    if page > 0:
        b.button(text="⬅️ قبلی" if locale == "fa" else "⬅️ Prev", callback_data=EmojiPageCB(page=page - 1).pack())
    if page + 1 < total_pages:
        b.button(text="➡️ بعدی" if locale == "fa" else "➡️ Next", callback_data=EmojiPageCB(page=page + 1).pack())
    b.button(text="✏️ افزودن ایموجی" if locale == "fa" else "✏️ Add Emoji", callback_data=EmojiActionCB(action="add_start").pack())
    b.button(text="🔙 بازگشت" if locale == "fa" else "🔙 Back", callback_data=MenuCB(section="account").pack())
    b.adjust(2, 2, 2, 1, 1)
    return b.as_markup()


def channels_keyboard(locale: str):
    b = InlineKeyboardBuilder()
    b.button(text="✏️ افزودن کانال" if locale == "fa" else "✏️ Add Channel", callback_data=ChannelCB(action="add_start").pack())
    b.button(text="🔙 بازگشت" if locale == "fa" else "🔙 Back", callback_data=MenuCB(section="account").pack())
    b.adjust(1, 1)
    return b.as_markup()


def support_keyboard(locale: str):
    b = InlineKeyboardBuilder()
    b.button(text="🦖 پیوی پشتیبانی" if locale == "fa" else "🦖 Support Chat", callback_data=SupportCB(action="chat").pack())
    b.button(text="🖼 ارسال تیکت" if locale == "fa" else "🖼 Open Ticket", callback_data=SupportCB(action="ticket").pack())
    b.button(text="🔙 بازگشت" if locale == "fa" else "🔙 Back", callback_data=MenuCB(section="main").pack())
    b.adjust(2, 1)
    return b.as_markup()


def admin_keyboard(locale: str):
    b = InlineKeyboardBuilder()
    b.button(text="📊 آمار دقیق" if locale == "fa" else "📊 Detailed Stats", callback_data=AdminCB(action="stats").pack())
    b.button(text="🔓 حذف محدودیت کاربر" if locale == "fa" else "🔓 Unlimit User", callback_data=AdminCB(action="unlimit").pack())
    b.button(text="📢 ارسال پیام همگانی" if locale == "fa" else "📢 Broadcast", callback_data=AdminCB(action="broadcast").pack())
    b.button(text="🔙 بازگشت" if locale == "fa" else "🔙 Back", callback_data=MenuCB(section="main").pack())
    b.adjust(1, 1, 1, 1)
    return b.as_markup()
