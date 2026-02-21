# Claude Telegram Bridge

Resume and interact with [Claude Code](https://docs.anthropic.com/en/docs/claude-code) sessions from Telegram.

## Prerequisites

- **Python 3.9+**
- **[Claude Code](https://docs.anthropic.com/en/docs/claude-code)** installed and on your PATH (`claude --version` should work)
- At least one prior Claude Code session (the bot reads from `~/.claude/history.jsonl`)

## Setup

### 1. Create a Telegram Bot

1. Message [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot` and follow the prompts
3. Copy the bot token

### 2. Get Your Telegram User ID

Message [@userinfobot](https://t.me/userinfobot) on Telegram to get your numeric user ID.

### 3. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your values:

```
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_USER_ID=your-numeric-user-id
```

### 4. Run

```bash
./start.sh
```

This will automatically:
1. Create a Python virtual environment (if not present)
2. Install all dependencies
3. Start the bot in the background
4. Save the process ID for management

**Stop the bot:**

```bash
./stop.sh
```

**View logs:**

```bash
tail -f logs/bot.log
```

### 5. Running as a Systemd Service (Optional)

For automatic startup on boot and crash recovery:

```bash
# Install the service (one-time)
sudo cp claude-telegram-bridge.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable claude-telegram-bridge.service

# Start / stop / restart
sudo systemctl start claude-telegram-bridge
sudo systemctl stop claude-telegram-bridge
sudo systemctl restart claude-telegram-bridge

# View logs
sudo journalctl -u claude-telegram-bridge -f
```

**Note:** When using systemd, do not use start.sh/stop.sh simultaneously. Choose one management method.

## Commands

| Command | Description |
|---|---|
| `/start` | Welcome message with available commands |
| `/sessions` | List recent sessions as tappable buttons |
| `/new` | Start a brand new Claude Code session |
| `/disconnect` | Disconnect from current session |
| `/status` | Show connection status and permission mode |
| `/safe` | Toggle permission mode (skip-permissions / safe) |

Tap a session button to connect, then send plain text messages to interact with Claude Code.

## Architecture

```
bot.py          # Telegram bot handlers + message dispatch
auth.py         # @authorized decorator (user ID check)
config.py       # Environment variables + constants
sessions.py     # Claude Code session discovery (reads ~/.claude/history.jsonl)
claude_cli.py   # Async wrapper around the `claude` CLI
```

- **Session discovery** reads Claude Code's own history and project files — no separate database needed.
- **Permission modes**: `skip-permissions` (default) auto-approves tool use. `safe` mode respects approval prompts, but note that `--print` mode cannot show interactive prompts, so this may cause the CLI to hang.
- **Message splitting** breaks long responses on newline boundaries to fit Telegram's 4,096-character limit.
- **CLI timeout** kills the process after 5 minutes to prevent runaway sessions.

## Security

Only the user matching `TELEGRAM_USER_ID` can interact with the bot. All other messages are silently ignored and logged as warnings.
