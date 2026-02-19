import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN: str = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_USER_ID: int = int(os.environ["TELEGRAM_USER_ID"])

CLAUDE_HISTORY_FILE: Path = Path.home() / ".claude" / "history.jsonl"
CLAUDE_PROJECTS_DIR: Path = Path.home() / ".claude" / "projects"

MAX_SESSIONS_DISPLAYED: int = 10
TELEGRAM_MAX_MESSAGE_LENGTH: int = 4096
CLI_TIMEOUT_SECONDS: int = 300  # 5 minutes
