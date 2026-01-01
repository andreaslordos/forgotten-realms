"""
Error Reporter Service

Automatically creates GitHub issues when runtime errors occur.
Used with the anthropics/claude-code-action to trigger automated TDD bug fixes.
"""

import hashlib
import logging
import os
import traceback
from collections import deque
from typing import Deque, List, Optional, Set

import httpx

logger = logging.getLogger(__name__)


class LogBuffer(logging.Handler):
    """A logging handler that keeps a rolling buffer of log entries."""

    def __init__(self, capacity: int = 200) -> None:
        super().__init__()
        self.capacity = capacity
        self.buffer: Deque[str] = deque(maxlen=capacity)
        self.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s:%(name)s:%(message)s")
        )

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            self.buffer.append(msg)
        except Exception:
            self.handleError(record)

    def get_logs(self) -> List[str]:
        """Return all buffered log entries."""
        return list(self.buffer)

    def get_logs_as_string(self) -> str:
        """Return all buffered logs as a single string."""
        return "\n".join(self.buffer)


# Global log buffer instance
_log_buffer: Optional[LogBuffer] = None


def install_log_buffer(capacity: int = 200) -> LogBuffer:
    """Install the log buffer on the root logger."""
    global _log_buffer
    if _log_buffer is None:
        _log_buffer = LogBuffer(capacity=capacity)
        logging.getLogger().addHandler(_log_buffer)
        logger.info(f"Log buffer installed (capacity: {capacity} lines)")
    return _log_buffer


def get_recent_logs() -> str:
    """Get recent logs from the buffer."""
    if _log_buffer is None:
        return "(Log buffer not installed)"
    return _log_buffer.get_logs_as_string()


class ErrorReporter:
    """Reports runtime errors as GitHub issues for automated fixing."""

    def __init__(
        self,
        github_token: Optional[str] = None,
        repo: Optional[str] = None,
    ) -> None:
        """
        Initialize the error reporter.

        Args:
            github_token: GitHub token with repo:issues permission.
                         Falls back to GITHUB_TOKEN env var.
            repo: GitHub repository in "owner/repo" format.
                  Falls back to GITHUB_REPO env var.
        """
        self.github_token = github_token or os.environ.get("GITHUB_TOKEN")
        self.repo = repo or os.environ.get("GITHUB_REPO")
        self.reported_signatures: Set[str] = set()
        self._enabled = bool(self.github_token and self.repo)
        if self._enabled:
            logger.info(f"ErrorReporter initialized for {self.repo}")
        else:
            missing = []
            if not self.github_token:
                missing.append("GITHUB_TOKEN")
            if not self.repo:
                missing.append("GITHUB_REPO")
            logger.warning(f"ErrorReporter disabled: {', '.join(missing)} not set")

    def _generate_signature(self, exception: Exception) -> str:
        """Generate a unique signature for deduplication."""
        tb = traceback.extract_tb(exception.__traceback__)
        last_frame = tb[-1] if tb else None

        sig_content = (
            f"{type(exception).__name__}:"
            f"{last_frame.filename if last_frame else ''}:"
            f"{last_frame.lineno if last_frame else ''}"
        )
        return hashlib.md5(sig_content.encode()).hexdigest()[:8]

    async def report(
        self,
        exception: Exception,
        command: Optional[str] = None,
        player: Optional[str] = None,
        room: Optional[str] = None,
    ) -> bool:
        """
        Report an error as a GitHub issue.

        Args:
            exception: The exception that occurred.
            command: The command that triggered the error.
            player: The player who triggered the error.
            room: The room where the error occurred.

        Returns:
            True if issue was created, False otherwise.
        """
        if not self._enabled:
            logger.debug("Error reporter disabled, skipping")
            return False

        # Deduplicate by error signature
        sig = self._generate_signature(exception)
        if sig in self.reported_signatures:
            logger.debug(f"Error already reported (signature: {sig}), skipping")
            return False
        self.reported_signatures.add(sig)
        logger.info(f"Reporting error to GitHub: {type(exception).__name__}")

        # Extract traceback info
        tb = traceback.extract_tb(exception.__traceback__)
        last_frame = tb[-1] if tb else None

        error_type = type(exception).__name__
        error_msg = str(exception)
        file_path = last_frame.filename if last_frame else "unknown"
        line_no = last_frame.lineno if last_frame else "?"
        func_name = last_frame.name if last_frame else "unknown"

        # Get recent logs
        recent_logs = get_recent_logs()

        issue_body = f"""## Runtime Error Report

**Error:** `{error_type}: {error_msg}`
**File:** `{file_path}:{line_no}`
**Function:** `{func_name}`
**Command:** `{command or 'N/A'}`
**Player:** `{player or 'N/A'}`
**Room:** `{room or 'N/A'}`

### Traceback
```
{traceback.format_exc()}
```

### Server Logs (last 200 lines before error)
<details>
<summary>Click to expand logs</summary>

```
{recent_logs}
```

</details>

---
*This issue was automatically created by the error reporter.*
"""

        issue_title = f"[BugFix] {error_type}: {error_msg[:50]}"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://api.github.com/repos/{self.repo}/issues",
                    headers={
                        "Authorization": f"token {self.github_token}",
                        "Accept": "application/vnd.github.v3+json",
                    },
                    json={
                        "title": issue_title,
                        "body": issue_body,
                        "labels": ["bug", "auto-fix"],
                    },
                    timeout=10.0,
                )
                response.raise_for_status()
                logger.info(f"GitHub issue created successfully: {issue_title}")
                return True
        except Exception as e:
            # Don't let error reporting cause more errors
            logger.error(f"Failed to create GitHub issue: {e}")
            return False


# Global instance - initialized lazily
_error_reporter: Optional[ErrorReporter] = None


def get_error_reporter() -> ErrorReporter:
    """Get the global error reporter instance."""
    global _error_reporter
    if _error_reporter is None:
        _error_reporter = ErrorReporter()
    return _error_reporter


async def report_error(
    exception: Exception,
    command: Optional[str] = None,
    player: Optional[str] = None,
    room: Optional[str] = None,
) -> bool:
    """
    Convenience function to report an error.

    Args:
        exception: The exception that occurred.
        command: The command that triggered the error.
        player: The player who triggered the error.
        room: The room where the error occurred.

    Returns:
        True if issue was created, False otherwise.
    """
    reporter = get_error_reporter()
    return await reporter.report(exception, command, player, room)
