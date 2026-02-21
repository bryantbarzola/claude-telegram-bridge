import asyncio
import json
import logging
import os
import shutil

from config import CLI_TIMEOUT_SECONDS

logger = logging.getLogger(__name__)


def _clean_env() -> dict[str, str]:
    """Return a copy of the environment with CLAUDECODE stripped to avoid nesting detection."""
    env = os.environ.copy()
    env.pop("CLAUDECODE", None)
    return env


async def send_message(
    session_id: str,
    message: str,
    cwd: str,
    skip_permissions: bool = True,
) -> str:
    """Send a message to a Claude Code session via CLI and return the response."""
    claude_path = shutil.which("claude")
    if claude_path is None:
        return "Error: 'claude' CLI not found on PATH."

    cmd = [
        claude_path,
        "--print",
        "--output-format", "text",
        "--resume", session_id,
    ]
    if skip_permissions:
        cmd.append("--dangerously-skip-permissions")
    cmd.append(message)

    logger.info("Running: %s (cwd=%s)", " ".join(cmd[:6]) + " ...", cwd)

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
            env=_clean_env(),
        )
    except FileNotFoundError:
        return "Error: 'claude' CLI not found."
    except OSError as e:
        return f"Error starting CLI: {e}"

    try:
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=CLI_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        process.kill()
        await process.wait()
        return f"Error: CLI timed out after {CLI_TIMEOUT_SECONDS} seconds. The process was killed."

    stdout_text = stdout.decode("utf-8", errors="replace").strip()
    stderr_text = stderr.decode("utf-8", errors="replace").strip()

    if process.returncode != 0:
        error_msg = f"CLI exited with code {process.returncode}."
        if "expired" in stderr_text.lower() or "credential" in stderr_text.lower():
            error_msg += "\n\nThis looks like an AWS credentials issue. Check your credentials."
        if stderr_text:
            # Truncate long stderr
            truncated = stderr_text[:1000] + ("..." if len(stderr_text) > 1000 else "")
            error_msg += f"\n\nstderr:\n{truncated}"
        return error_msg

    if not stdout_text:
        return "(empty response)"

    return stdout_text


async def send_new_message(
    message: str,
    cwd: str,
    skip_permissions: bool = True,
) -> tuple[str, str | None]:
    """Start a new Claude Code session and return (response_text, session_id).

    Uses --output-format json to capture the session_id from the first response.
    Returns (error_message, None) if something goes wrong.
    """
    claude_path = shutil.which("claude")
    if claude_path is None:
        return ("Error: 'claude' CLI not found on PATH.", None)

    cmd = [
        claude_path,
        "--print",
        "--output-format", "json",
    ]
    if skip_permissions:
        cmd.append("--dangerously-skip-permissions")
    cmd.append(message)

    logger.info("Starting new session: %s (cwd=%s)", " ".join(cmd[:5]) + " ...", cwd)

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
            env=_clean_env(),
        )
    except FileNotFoundError:
        return ("Error: 'claude' CLI not found.", None)
    except OSError as e:
        return (f"Error starting CLI: {e}", None)

    try:
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=CLI_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        process.kill()
        await process.wait()
        return (f"Error: CLI timed out after {CLI_TIMEOUT_SECONDS} seconds. The process was killed.", None)

    stdout_text = stdout.decode("utf-8", errors="replace").strip()
    stderr_text = stderr.decode("utf-8", errors="replace").strip()

    if process.returncode != 0:
        error_msg = f"CLI exited with code {process.returncode}."
        if stderr_text:
            truncated = stderr_text[:1000] + ("..." if len(stderr_text) > 1000 else "")
            error_msg += f"\n\nstderr:\n{truncated}"
        return (error_msg, None)

    if not stdout_text:
        return ("(empty response)", None)

    try:
        data = json.loads(stdout_text)
    except json.JSONDecodeError:
        return (stdout_text, None)

    session_id = data.get("session_id")
    result_text = data.get("result", "")

    if data.get("is_error"):
        return (f"Claude error: {result_text}", session_id)

    return (result_text or "(empty response)", session_id)
