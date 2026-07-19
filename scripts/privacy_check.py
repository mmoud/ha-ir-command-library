"""Fail CI when common private Home Assistant artifacts enter the repository."""

from __future__ import annotations

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SKIP = {".git", "__pycache__", ".pytest_cache"}
TEXT_SUFFIXES = {
    ".css", ".html", ".js", ".json", ".md", ".py", ".svg", ".txt", ".yaml", ".yml"
}

PATTERNS = {
    "private IPv4 address": re.compile(
        r"\b(?:10(?:\.\d{1,3}){3}|192\.168(?:\.\d{1,3}){2}|172\.(?:1[6-9]|2\d|3[01])(?:\.\d{1,3}){2})\b"
    ),
    "Home Assistant long-lived token": re.compile(r"\beyJ[A-Za-z0-9_-]{80,}\b"),
    "BroadLink payload": re.compile(r"\bb64:[A-Za-z0-9+/]{40,}={0,2}\b"),
    "HomeKit pairing code": re.compile(r"\b\d{3}-\d{2}-\d{3}\b"),
    "storage or secrets path": re.compile(r"(?:^|/)(?:\.storage|secrets\.ya?ml)(?:/|$)"),
}


def main() -> int:
    findings: list[str] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        if any(part in SKIP for part in path.parts):
            continue
        relative = path.relative_to(ROOT)
        text = path.read_text(encoding="utf-8", errors="replace")
        for label, pattern in PATTERNS.items():
            if pattern.search(text) or pattern.search(relative.as_posix()):
                findings.append(f"{relative}: {label}")
    if findings:
        print("Privacy check failed:")
        print("\n".join(f"- {item}" for item in findings))
        return 1
    print("Privacy check passed: no blocked private-data patterns found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
