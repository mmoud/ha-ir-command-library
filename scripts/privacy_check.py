"""Block common private Home Assistant artifacts from public releases.

The check covers the checkout and all reachable Git blobs. Checking history is
important: making a repository public exposes every reachable commit, not only
the files at ``HEAD``.
"""

from __future__ import annotations

from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRECTORIES = {".git", "__pycache__", ".pytest_cache", ".ruff_cache"}

CONTENT_PATTERNS = {
    "private IPv4 address": re.compile(
        r"\b(?:10(?:\.\d{1,3}){3}|192\.168(?:\.\d{1,3}){2}|172\.(?:1[6-9]|2\d|3[01])(?:\.\d{1,3}){2})\b"
    ),
    "Home Assistant long-lived token": re.compile(r"\beyJ[A-Za-z0-9_-]{80,}\b"),
    "BroadLink payload": re.compile(r"\bb64:[A-Za-z0-9+/]{40,}={0,2}\b"),
    "HomeKit pairing code": re.compile(r"\b\d{3}-\d{2}-\d{3}\b"),
    "MAC address": re.compile(r"\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b"),
    "private email address": re.compile(
        r"\b[A-Za-z0-9._%+-]+@(?!users\.noreply\.github\.com\b)[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
    ),
    "likely literal credential": re.compile(
        r"(?i)\b(?:api[_-]?key|access[_-]?token|auth[_-]?token|password|secret)\b\s*[:=]\s*['\"]?(?!\$|REPLACE_ME|<)[A-Za-z0-9_./+=-]{20,}"
    ),
}

SENSITIVE_PATH = re.compile(
    r"(?i)(?:^|/)(?:\.storage(?:/|$)|secrets\.ya?ml$|\.env(?:\.[^/]+)?$|[^/]+\.(?:pem|key|p12|pfx|der)$)"
)


def _scan(label: str, content: bytes) -> list[str]:
    """Return privacy findings for one path/blob without printing its content."""
    findings: list[str] = []
    if SENSITIVE_PATH.search(label):
        findings.append(f"{label}: sensitive configuration or key file")
    text = content.decode("utf-8", errors="replace")
    for name, pattern in CONTENT_PATTERNS.items():
        if pattern.search(text):
            findings.append(f"{label}: {name}")
    return findings


def _working_tree_findings() -> list[str]:
    findings: list[str] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or any(part in SKIP_DIRECTORIES for part in path.parts):
            continue
        findings.extend(_scan(path.relative_to(ROOT).as_posix(), path.read_bytes()))
    return findings


def _git(*args: str, text: bool = False) -> str | bytes:
    """Run Git in the repository root and return stdout."""
    return subprocess.check_output(["git", *args], cwd=ROOT, text=text)


def _history_findings() -> list[str]:
    """Scan every unique blob reachable from local refs."""
    try:
        commits = _git("rev-list", "--all", text=True).splitlines()
    except (OSError, subprocess.CalledProcessError) as err:
        return [f"Git history could not be scanned: {err}"]

    findings: list[str] = []
    seen_blobs: set[str] = set()
    for commit in commits:
        tree = _git("ls-tree", "-r", "-z", commit)
        for record in tree.split(b"\0"):
            if not record:
                continue
            metadata, path = record.split(b"\t", 1)
            _mode, object_type, object_id = metadata.decode().split()
            if object_type != "blob" or object_id in seen_blobs:
                continue
            seen_blobs.add(object_id)
            content = _git("cat-file", "blob", object_id)
            findings.extend(_scan(f"{commit[:12]}:{path.decode(errors='replace')}", content))
    return findings


def main() -> int:
    findings = _working_tree_findings() + _history_findings()
    if findings:
        print("Privacy check failed:")
        print("\n".join(f"- {item}" for item in sorted(set(findings))))
        return 1
    print("Privacy check passed: working tree and reachable Git history are clean.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
