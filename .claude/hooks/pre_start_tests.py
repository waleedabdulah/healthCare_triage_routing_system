"""
Claude Code PreToolUse hook — runs the full test suite before the backend starts.

Triggered by: any Bash tool call containing "uvicorn src.api.main:app"
Blocks startup if any test fails (exit code 2 = block in Claude Code hooks).
Passes through silently for all other Bash commands.
"""
import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
VENV_PYTHON  = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"


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
    )

    if result.returncode != 0:
        print("=" * 60, file=sys.stderr)
        print("BLOCKED: Test suite failed.", file=sys.stderr)
        print("Fix the failing tests before starting the backend.", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        sys.exit(2)   # exit code 2 = Claude Code blocks the tool call

    print("=" * 60, flush=True)
    print("All tests passed. Proceeding to start the backend.", flush=True)
    print("=" * 60, flush=True)
    sys.exit(0)


if __name__ == "__main__":
    main()
