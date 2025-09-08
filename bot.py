# bot.py
# Main anonymous chat bot with UI separated into ui.py
# Surveillance logic calls are delegated to surveillance.py (do NOT modify if you want to keep your original surveillance module).

import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, ContextTypes,
    MessageHandler, CallbackQueryHandler, filters
)
from telegram.error import Forbidden, BadRequest, TimedOut
import asyncio

from ui import get_start_message, main_menu_markup, in_chat_markup, partner_left_markup
import surveillance  # <<-- Replace or keep this module; it's intentionally isolated.

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")

# Parse admin IDs safely
ADMIN_IDS = []
for x in os.getenv("ADMIN_IDS", "").split(","):
    x = x.strip()
    if x:
        try:
            ADMIN_IDS.append(int(x))
        except ValueError:
            print(f"[WARN] Ignoring invalid ADMIN_ID value: {x}")

# Parse SPECTATOR_GROUP_ID safely
SPECTATOR_GROUP_ID = os.getenv("SPECTATOR_GROUP_ID")
if SPECTATOR_GROUP_ID:
    try:
        SPECTATOR_GROUP_ID = int(SPECTATOR_GROUP_ID)
    except ValueError:
        print(f"[WARN] Invalid SPECTATOR_GROUP_ID: {SPECTATOR_GROUP_ID}")
        SPECTATOR_GROUP_ID = None


# matchmaking state
waiting_users = asyncio.Queue()
active_chats = {}  # user_id -> partner_id
blocked_users = set()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome / onboarding."""
    user = update.effective_user
    user_id = user.id
    # If blocked, politely inform
    if user_id in blocked_users:
        await update.message.reply_text("You are blocked from using this service.")
        return

    # Send welcome UI from ui.py
    try:
        await update.message.reply_markdown(get_start_message(), reply_markup=main_menu_markup())
    except Exception as e:
        logger.exception("Failed to send start message: %s", e)
        # fallback simple message
        await update.message.reply_text("Welcome. Use /start to begin.")

async def getid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    await update.message.reply_text(f"📌 This group ID is: `{chat.id}`")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "ℹ️ *How to use*\n"
        "• Tap *Start Chat* to be paired with a random anonymous user.\n"
        "• Use *Report* to flag abusive messages. The team monitors conversations.\n"
        "• Use *End Chat* to leave a conversation.\n\n"
        "Commands:\n"
        "/start - open the menu\n"
        "/stop - end current chat\n        "
    )
    await update.message.reply_markdown(text)

async def join_matching(user_id: int):
    """Helper to add a user to the waiting queue."""
    await waiting_users.put(user_id)

async def pair_waiting_users(app):
    """
    Background pairing loop. This runs implicitly via enqueueing approach; 
    but keep as a helper if you want scheduled pairing logic.
    """
    # Not used directly; pairing happens within start_match handling below.
    pass

async def start_match_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Begins matchmaking for the caller."""
    user = update.effective_user
    user_id = user.id

    if user_id in active_chats:
        await update.callback_query.answer("You're already connected.")
        return

    # Put user in queue and try to pair
    await join_matching(user_id)
    await update.callback_query.answer("Searching for a partner...")

    # Try to immediately pair with another waiting user
    try:
        # Wait a short period for another user to join
        partner_id = None
        try:
            # if there is another waiting user not equal to user_id, pair them
            # loop queue to find a different user (non-blocking)
            tmp = []
            while not waiting_users.empty():
                candidate = waiting_users.get_nowait()
                if candidate != user_id and candidate not in active_chats and candidate not in blocked_users:
                    partner_id = candidate
                    break
                else:
                    tmp.append(candidate)
            # put back leftover candidates
            for t in tmp:
                await waiting_users.put(t)
        except Exception:
            partner_id = None

        # If no partner found currently, wait a little for someone to join
        if not partner_id:
            try:
                # Wait up to 12 seconds for another user to join
                candidate = await asyncio.wait_for(waiting_users.get(), timeout=12)
                if candidate != user_id and candidate not in active_chats and candidate not in blocked_users:
                    partner_id = candidate
                else:
                    # put back if unsuitable
                    await waiting_users.put(candidate)
            except asyncio.TimeoutError:
                partner_id = None

        if not partner_id:
            # No partner found — inform user and keep them in queue
            await update.callback_query.message.reply_text("🔎 Still searching... Tap Start Chat again or wait a moment.")
            # ensure they are back in queue for future pairing
            await waiting_users.put(user_id)
            return

        # Pair them
        active_chats[user_id] = partner_id
        active_chats[partner_id] = user_id

        # Send connected messages to both
        try:
            await context.bot.send_message(user_id, "✅ *Connected — say hi!*", reply_markup=in_chat_markup(), parse_mode="Markdown")
            await context.bot.send_message(partner_id, "✅ *Connected — say hi!*", reply_markup=in_chat_markup(), parse_mode="Markdown")
        except (Forbidden, BadRequest) as e:
            logger.warning("Failed to notify one of the partners: %s", e)
            # Clean up
            active_chats.pop(user_id, None)
            active_chats.pop(partner_id, None)
            await update.callback_query.message.reply_text("Could not connect — partner might have privacy settings.")
            return

        # Notify surveillance module (non-invasive)
        try:
            await surveillance.on_pair_created(context.bot, user_id, partner_id)
        except Exception as e:
            logger.warning("surveillance.on_pair_created failed: %s", e)

    except Exception as e:
        logger.exception("Error in start_match_handler: %s", e)
        await update.callback_query.message.reply_text("Error while searching. Try again.")

async def end_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """End the chat for user who pressed End Chat (callback) or /stop command."""
    user = update.effective_user
    user_id = user.id
    if user_id not in active_chats:
        await update.callback_query.answer("You're not in a chat.")
        # also handle text-based /stop
        return

    partner = active_chats.pop(user_id, None)
    if partner:
        active_chats.pop(partner, None)
        try:
            await context.bot.send_message(partner, "🛑 Your partner left.", reply_markup=partner_left_markup())
        except Exception:
            pass

    try:
        await update.callback_query.message.reply_text("🛑 Chat ended for you.", reply_markup=main_menu_markup())
    except Exception:
        pass

    # Notify surveillance
    try:
        await surveillance.on_chat_ended(context.bot, user_id, partner)
    except Exception as e:
        logger.warning("surveillance.on_chat_ended failed: %s", e)

async def reconnect_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User wants to find another partner — end current chat first then start matchmaking."""
    user = update.effective_user
    user_id = user.id
    # end existing chat if any
    if user_id in active_chats:
        partner = active_chats.pop(user_id, None)
        if partner:
            active_chats.pop(partner, None)
            try:
                await context.bot.send_message(partner, "🔁 Your partner reconnected elsewhere.", reply_markup=partner_left_markup())
            except Exception:
                pass
    # enqueue and try match
    await start_match_handler(update, context)

async def report_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Report current partner — mark to surveillance and optionally end chat."""
    user = update.effective_user
    user_id = user.id
    partner_id = active_chats.get(user_id)
    await update.callback_query.answer("Reported. Thank you — appropriate team will review.")

    # Inform surveillance / reporting system
    try:
        await surveillance.on_user_reported(context.bot, reporter_id=user_id, reported_id=partner_id, reason="Reported via UI")
    except Exception as e:
        logger.warning("surveillance.on_user_reported failed: %s", e)

async def block_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    partner_id = active_chats.get(user_id)
    # Add partner to blocked list if present
    if partner_id:
        blocked_users.add(partner_id)
        # end partner's chat
        try:
            await context.bot.send_message(partner_id, "🚫 You have been blocked by your partner.", reply_markup=partner_left_markup())
        except Exception:
            pass
        # remove both from active mapping
        active_chats.pop(user_id, None)
        active_chats.pop(partner_id, None)
    await update.callback_query.answer("Blocked.")
    try:
        await update.callback_query.message.reply_text("User blocked and chat ended.", reply_markup=main_menu_markup())
    except Exception:
        pass

async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.callback_query.message.reply_text("Returned to main menu.", reply_markup=main_menu_markup())
    except Exception:
        pass

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Central callback data router."""
    query = update.callback_query
    data = query.data
    if data == "start_match":
        await start_match_handler(update, context)
    elif data == "end_chat":
        await end_chat(update, context)
    elif data == "reconnect":
        await reconnect_handler(update, context)
    elif data == "report":
        await report_handler(update, context)
    elif data == "block":
        await block_handler(update, context)
    elif data == "help":
        await help_cmd(update, context)
    elif data == "settings":
        await query.answer("Settings are currently minimal. Contact admins for changes.")
    elif data == "back_to_menu":
        await back_to_menu(update, context)
    else:
        await query.answer()

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Relay messages between chat partners and notify surveillance module."""
    user = update.effective_user
    user_id = user.id

    # If user is not in an active chat, ignore or suggest Start Chat
    if user_id not in active_chats:
        try:
            await update.message.reply_text("You're not connected. Tap *Start Chat* to find a partner.", parse_mode="Markdown", reply_markup=main_menu_markup())
        except Exception:
            pass
        return

    partner_id = active_chats.get(user_id)
    if not partner_id:
        await update.message.reply_text("Partner unavailable. Try reconnecting.", reply_markup=main_menu_markup())
        return

    # Forward text and non-text messages
    try:
        # If it's text
        if update.message.text:
    await context.bot.send_message(partner_id, update.message.text)
else:
    # Use copy_message to preserve anonymity
    try:
        await context.bot.copy_message(
            chat_id=partner_id,
            from_chat_id=update.message.chat.id,
            message_id=update.message.message_id
        )
    except Exception as e:
        logger.warning(f"Failed to copy message anonymously: {e}")


        # Notify surveillance about message (non-invasive wrapper)
        try:
            await surveillance.on_message(context.bot, from_id=user_id, to_id=partner_id, message=update.message)
        except Exception as e:
            logger.warning("surveillance.on_message error: %s", e)

    except (Forbidden, BadRequest, TimedOut) as e:
        logger.warning("Failed to deliver message: %s", e)
        # End chat if partner can't be messaged
        active_chats.pop(user_id, None)
        active_chats.pop(partner_id, None)
        try:
            await update.message.reply_text("Delivery failed. Chat ended.", reply_markup=main_menu_markup())
        except Exception:
            pass

def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN environment variable is required.")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", lambda u, c: end_chat(u, c)))
    app.add_handler(CommandHandler("getid", getid))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, message_handler))

    logger.info("Starting bot...")
    app.run_polling()

if __name__ == "__main__":
    main()
      
