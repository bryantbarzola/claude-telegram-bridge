from __future__ import annotations

import logging
from dataclasses import dataclass

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from auth import authorized
from claude_cli import send_message
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_MAX_MESSAGE_LENGTH
from sessions import get_session_by_id, list_recent_sessions

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


@dataclass
class BotState:
    session_id: str | None = None
    session_cwd: str | None = None
    session_label: str = ""
    skip_permissions: bool = True


state = BotState()


def split_message(text: str, max_length: int = TELEGRAM_MAX_MESSAGE_LENGTH) -> list[str]:
    """Split text into chunks on newline boundaries."""
    if len(text) <= max_length:
        return [text]

    chunks: list[str] = []
    current = ""
    for line in text.split("\n"):
        # +1 for the newline character we'll add back
        if current and len(current) + len(line) + 1 > max_length:
            chunks.append(current)
            current = ""
        if len(line) > max_length:
            # Line itself exceeds max — hard-split it
            if current:
                chunks.append(current)
                current = ""
            for i in range(0, len(line), max_length):
                chunks.append(line[i : i + max_length])
        else:
            current = current + "\n" + line if current else line

    if current:
        chunks.append(current)
    return chunks


@authorized
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Claude Code Bridge\n\n"
        "Commands:\n"
        "/sessions - List recent sessions\n"
        "/disconnect - Disconnect from session\n"
        "/status - Show connection status\n"
        "/safe - Toggle permission mode\n\n"
        "Connect to a session, then send messages to interact with Claude Code."
    )


@authorized
async def sessions_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    recent = list_recent_sessions()
    if not recent:
        await update.message.reply_text("No recent sessions found.")
        return

    buttons = []
    for s in recent:
        label = s.display if s.display else s.session_id[:12]
        # Truncate label to fit Telegram button limits
        if len(label) > 60:
            label = label[:57] + "..."
        buttons.append([InlineKeyboardButton(label, callback_data=f"connect:{s.session_id}")])

    await update.message.reply_text(
        "Recent sessions (tap to connect):",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


@authorized
async def session_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    data = query.data
    if not data.startswith("connect:"):
        return

    session_id = data[len("connect:"):]
    session = get_session_by_id(session_id)
    if session is None:
        await query.edit_message_text("Session not found. It may have been deleted.")
        return

    state.session_id = session.session_id
    state.session_cwd = session.cwd
    state.session_label = session.display or session.session_id[:12]

    mode = "skip-permissions" if state.skip_permissions else "safe"
    await query.edit_message_text(
        f"Connected to: {state.session_label}\n"
        f"Project: {session.project}\n"
        f"Working dir: {session.cwd}\n"
        f"Mode: {mode}\n\n"
        "Send a message to interact with this session."
    )


@authorized
async def disconnect_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if state.session_id is None:
        await update.message.reply_text("Not connected to any session.")
        return

    label = state.session_label
    state.session_id = None
    state.session_cwd = None
    state.session_label = ""
    await update.message.reply_text(f"Disconnected from: {label}")


@authorized
async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if state.session_id is None:
        connected = "Not connected"
    else:
        connected = f"Connected to: {state.session_label}\nSession ID: {state.session_id}\nWorking dir: {state.session_cwd}"

    mode = "skip-permissions" if state.skip_permissions else "safe"
    await update.message.reply_text(f"{connected}\nMode: {mode}")


@authorized
async def safe_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    state.skip_permissions = not state.skip_permissions

    if state.skip_permissions:
        await update.message.reply_text(
            "Mode: skip-permissions\n"
            "Claude will execute tools without asking for approval."
        )
    else:
        await update.message.reply_text(
            "Mode: safe\n"
            "WARNING: In --print mode, Claude cannot prompt for interactive permission "
            "approval. Commands requiring approval may cause the CLI to hang. "
            "Use /safe again to switch back if this happens."
        )


@authorized
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if state.session_id is None:
        await update.message.reply_text("Not connected. Use /sessions to pick a session.")
        return

    user_text = update.message.text
    if not user_text:
        return

    thinking_msg = await update.message.reply_text("Thinking...")

    response = await send_message(
        session_id=state.session_id,
        message=user_text,
        cwd=state.session_cwd,
        skip_permissions=state.skip_permissions,
    )

    chunks = split_message(response)

    # Edit the "Thinking..." message with the first chunk
    await thinking_msg.edit_text(chunks[0])

    # Send remaining chunks as new messages
    for chunk in chunks[1:]:
        await update.message.reply_text(chunk)


def main() -> None:
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("sessions", sessions_command))
    app.add_handler(CommandHandler("disconnect", disconnect_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("safe", safe_command))
    app.add_handler(CallbackQueryHandler(session_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot starting...")
    app.run_polling()


if __name__ == "__main__":
    main()
