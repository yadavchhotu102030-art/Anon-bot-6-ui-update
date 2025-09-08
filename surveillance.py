# surveillance.py
# This module is intentionally isolated so your monitoring/surveillance code can live here.
# If you already have a surveillance implementation (that watches and logs all messages),
# replace the contents of this file with your original functions but keep the same API signatures below,
# or import and call your original code from these functions.
#
# DO NOT CHANGE THE CALLS FROM bot.py. Instead, change implementations here if needed.

import os
import logging
from telegram import Bot

logger = logging.getLogger(__name__)
SPECTATOR_GROUP_ID = os.getenv("SPECTATOR_GROUP_ID")

async def on_pair_created(bot: Bot, user_a: int, user_b: int):
    """Called when two users get paired. Use this to create audit logs or notify supervisors."""
    try:
        if SPECTATOR_GROUP_ID:
            await bot.send_message(int(SPECTATOR_GROUP_ID), f"🔗 Pair created: {user_a} ↔ {user_b}")
    except Exception as e:
        logger.warning("surv on_pair_created error: %s", e)

async def on_chat_ended(bot: Bot, user_a: int, user_b: int):
    """Called when a chat ends."""
    try:
        if SPECTATOR_GROUP_ID:
            await bot.send_message(int(SPECTATOR_GROUP_ID), f"🚪 Chat ended: {user_a} ↔ {user_b}")
    except Exception as e:
        logger.warning("surv on_chat_ended error: %s", e)

async def on_user_reported(bot: Bot, reporter_id: int, reported_id: int, reason: str = ""):
    """Report event. The real implementation should log, store, and forward evidence to the crime bureau."""
    try:
        if SPECTATOR_GROUP_ID:
            await bot.send_message(int(SPECTATOR_GROUP_ID),
                                   f"🚩 Report: reporter={reporter_id}, reported={reported_id}, reason={reason}")
    except Exception as e:
        logger.warning("surv on_user_reported error: %s", e)

async def on_message(bot: Bot, from_id: int, to_id: int, message):
    """
    Called when a message is relayed from from_id to to_id.
    The 'message' is the telegram.Message object; the real surveillance system might
    store message.data, attachments details, forward to observers, etc.
    """
    try:
        preview = message.text or "[non-text message]"
        if SPECTATOR_GROUP_ID:
            await bot.send_message(int(SPECTATOR_GROUP_ID), f"👁 {from_id} → {to_id}\n💬 {preview}")
    except Exception as e:
        logger.warning("surv on_message error: %s", e)
      
