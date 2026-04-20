"""
Build log script — runs the full test suite and appends a timestamped
entry (with git info, Python version, and full pytest output) to
logs/build.log.

Usage:
    .venv/Scripts/python.exe scripts/build_log.py           # full suite
    .venv/Scripts/python.exe scripts/build_log.py booking   # filter by name
    .venv/Scripts/python.exe scripts/build_log.py triage
    .venv/Scripts/python.exe scripts/build_log.py auth
    .venv/Scripts/python.exe scripts/build_log.py admin
"""
import subprocess
import sys
import platform
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOG_FILE     = PROJECT_ROOT / "logs" / "build.log"
VENV_PYTHON  = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
SEPARATOR    = "=" * 70


def _git_info() -> tuple[str, str]:
    """Return (branch, 'short_hash message') or fallback strings."""
    try:
        branch = subprocess.check_output(
            ["git", "branch", "--show-current"], cwd=PROJECT_ROOT, text=True
        ).strip()
        commit = subprocess.check_output(
            ["git", "log", "-1", "--format=%h %s"], cwd=PROJECT_ROOT, text=True
        ).strip()
        return branch, commit
    except Exception:
        return "unknown", "unknown"


def _python_version() -> str:
    out = subprocess.check_output(
        [str(VENV_PYTHON), "--version"], cwd=PROJECT_ROOT, text=True
    ).strip()
    return out


def run_build(filter_arg: str | None = None, trigger: str = "manual") -> int:
    """Run pytest, tee output to stdout and append to build.log. Returns exit code."""
    LOG_FILE.parent.mkdir(exist_ok=True)

    cmd = [str(VENV_PYTHON), "-m", "pytest", "tests/", "-v", "--tb=short"]
    if filter_arg:
        cmd += ["-k", filter_arg]

    timestamp   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    branch, commit = _git_info()
    py_version  = _python_version()
    filter_str  = filter_arg if filter_arg else "(none — full suite)"

    header = (
        f"\n{SEPARATOR}\n"
        f"  BUILD LOG ENTRY\n"
        f"  timestamp : {timestamp}\n"
        f"  trigger   : {trigger}\n"
        f"  branch    : {branch}\n"
        f"  commit    : {commit}\n"
        f"  python    : {py_version}\n"
        f"  filter    : {filter_str}\n"
        f"{SEPARATOR}\n"
    )

    print(header, flush=True)

    # Run pytest — capture output for log, also stream to terminal
    result = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)
    combined = result.stdout + result.stderr

    print(combined, flush=True)

    # Extract summary line (last line containing "passed" / "failed" / "error")
    lines = combined.splitlines()
    summary = next(
        (l.strip() for l in reversed(lines)
         if any(k in l for k in ("passed", "failed", "error", "no tests"))),
        "no summary line found"
    )
    status = "PASS" if result.returncode == 0 else "FAIL"

    footer = (
        f"\n{SEPARATOR}\n"
        f"  STATUS  : {status}\n"
        f"  SUMMARY : {summary}\n"
        f"{SEPARATOR}\n"
    )

    print(footer, flush=True)

    # Append full entry to log file
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(header)
        f.write(combined)
        f.write(footer)

    print(f"  Log appended -> {LOG_FILE}", flush=True)
    return result.returncode


if __name__ == "__main__":
    filter_arg = sys.argv[1] if len(sys.argv) > 1 else None
    sys.exit(run_build(filter_arg, trigger="manual"))
