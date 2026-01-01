"""
Error Reporter Service

Automatically creates GitHub issues when runtime errors occur.
Used with the anthropics/claude-code-action to trigger automated TDD bug fixes.
"""

import hashlib
import os
import traceback
from typing import Optional, Set

import httpx


class ErrorReporter:
    """Reports runtime errors as GitHub issues for automated fixing."""

    def __init__(
        self,
        github_token: Optional[str] = None,
        repo: str = "andreas/forgotten-realms",
    ) -> None:
        """
        Initialize the error reporter.

        Args:
            github_token: GitHub token with repo:issues permission.
                         Falls back to GITHUB_TOKEN env var.
            repo: GitHub repository in "owner/repo" format.
        """
        self.github_token = github_token or os.environ.get("GITHUB_TOKEN")
        self.repo = repo
        self.reported_signatures: Set[str] = set()
        self._enabled = bool(self.github_token)

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
            return False

        # Deduplicate by error signature
        sig = self._generate_signature(exception)
        if sig in self.reported_signatures:
            return False
        self.reported_signatures.add(sig)

        # Extract traceback info
        tb = traceback.extract_tb(exception.__traceback__)
        last_frame = tb[-1] if tb else None

        error_type = type(exception).__name__
        error_msg = str(exception)
        file_path = last_frame.filename if last_frame else "unknown"
        line_no = last_frame.lineno if last_frame else "?"
        func_name = last_frame.name if last_frame else "unknown"

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

---
*This issue was automatically created by the error reporter.*
*Add the `auto-fix` label to trigger Claude Code to fix this bug using TDD.*
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
                return True
        except Exception:
            # Don't let error reporting cause more errors
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
