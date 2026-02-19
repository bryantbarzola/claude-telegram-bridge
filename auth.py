import functools
import logging

from telegram import Update
from telegram.ext import ContextTypes

from config import TELEGRAM_USER_ID

logger = logging.getLogger(__name__)


def authorized(func):
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id if update.effective_user else None
        if user_id != TELEGRAM_USER_ID:
            logger.warning("Unauthorized access attempt from user_id=%s", user_id)
            return
        return await func(update, context)
    return wrapper
