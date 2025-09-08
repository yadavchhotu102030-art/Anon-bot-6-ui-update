# ui.py - Non-invasive UI templates & helpers for Anon Telegram Bot
# Edit this file to tweak text, emojis, button labels and layouts.

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def get_start_message():
    return (
        "👋 *Welcome to AnonChat*\n\n"
        "Stay anonymous — connect with strangers safely. "
        "Tap *Start Chat* to find someone to talk to.\n\n"
        "⚠️ *Note:* Conversations may be monitored by authorized personnel for safety and compliance."
    )

def main_menu_markup():
    kb = [
        [InlineKeyboardButton('🔎 Start Chat', callback_data='start_match')],
        [InlineKeyboardButton('❓ Help', callback_data='help'), InlineKeyboardButton('⚙️ Settings', callback_data='settings')],
    ]
    return InlineKeyboardMarkup(kb)

def in_chat_markup():
    kb = [
        [InlineKeyboardButton('⛔ End Chat', callback_data='end_chat'), InlineKeyboardButton('🔁 Reconnect', callback_data='reconnect')],
        [InlineKeyboardButton('🚩 Report', callback_data='report'), InlineKeyboardButton('🔕 Block', callback_data='block')],
    ]
    return InlineKeyboardMarkup(kb)

def partner_left_markup():
    kb = [
        [InlineKeyboardButton('🔁 Find another', callback_data='reconnect')],
        [InlineKeyboardButton('🏠 Back to menu', callback_data='back_to_menu')],
    ]
    return InlineKeyboardMarkup(kb)
  
