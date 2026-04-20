"""
Claude Code PreToolUse hook — runs the full test suite before the backend starts.

Triggered by: any Bash tool call containing "uvicorn src.api.main:app"
Blocks startup if any test fails (exit code 2 = block in Claude Code hooks).
Appends a one-line summary to logs/build.log after every run.
Passes through silently for all other Bash commands.
"""
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
LOG_FILE     = PROJECT_ROOT / "logs" / "build.log"
VENV_PYTHON  = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"


def _append_hook_log(status: str, summary: str) -> None:
    """Append a one-line entry to logs/build.log."""
    try:
        LOG_FILE.parent.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{timestamp}] PRE-START HOOK | STATUS: {status} | {summary}\n"
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass  # never crash the hook due to logging failure


def _extract_summary(output: str) -> str:
    """Pull the pytest summary line from captured output."""
    lines = output.splitlines()
    return next(
        (l.strip() for l in reversed(lines)
         if any(k in l for k in ("passed", "failed", "error", "no tests"))),
        "no summary available"
    )


def main() -> None:
    # Claude Code passes tool input as JSON on stdin
    try:
        raw = sys.stdin.read()
        tool_input = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        tool_input = {}

    command: str = tool_input.get("command", "")

    # Only intercept backend startup — let every other Bash call through
    if "uvicorn" not in command or "src.api.main:app" not in command:
        sys.exit(0)

    print("=" * 60, flush=True)
    print("Pre-start check: running test suite...", flush=True)
    print("=" * 60, flush=True)

    result = subprocess.run(
        [str(VENV_PYTHON), "-m", "pytest", "tests/", "-v", "--tb=short"],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
    )

    combined = result.stdout + result.stderr
    print(combined, flush=True)

    summary = _extract_summary(combined)

    if result.returncode != 0:
        _append_hook_log("FAIL", summary)
        print("=" * 60, file=sys.stderr)
        print("BLOCKED: Test suite failed.", file=sys.stderr)
        print("Fix the failing tests before starting the backend.", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        sys.exit(2)   # exit code 2 = Claude Code blocks the tool call

    _append_hook_log("PASS", summary)
    print("=" * 60, flush=True)
    print("All tests passed. Proceeding to start the backend.", flush=True)
    print("=" * 60, flush=True)
    sys.exit(0)


if __name__ == "__main__":
    main()
