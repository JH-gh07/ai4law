"""Fail fast when generated, runtime, or credential-bearing files enter Git."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_EXACT = {
    ".DS_Store",
    ".claude/settings.local.json",
    ".streamlit/config.toml",
    ".vscode/settings.json",
    "IMPLEMENTATION_VERIFICATION.md",
    "architecture.html",
    "docknowledge.md",
    "planv0.md",
    "doc/.DS_Store",
    "frontend/vite.config.d.ts",
    "frontend/vite.config.js",
    "storage/ai4law.db",
    "storage/runtime_settings.json",
}
FORBIDDEN_PREFIXES = (
    ".vite/",
    ".superpowers/",
    "ai_engine/",
    "doc/knowledge/index/",
    "doc/knowledge/normalized/",
    "doc/knowledge/registry/",
    "frontend/.codex-archives/",
    "frontend/storage/",
    "frontend/tmp/",
    "storage/drafts/",
    "storage/rag/",
    "storage/reports/",
    "storage/traces/",
    "storage/uploads/",
)
FORBIDDEN_SEGMENTS = {"__pycache__", "node_modules", ".pytest_cache", ".vite"}
FORBIDDEN_SUFFIXES = (".pyc", ".pyo", ".tsbuildinfo")
ACTIVE_TEXT_PREFIXES = ("backend/", "frontend/src/", "scripts/")
SECRET_PATTERNS = {
    "embedded competition credential": re.compile(r"DELILEGAL_COMPETITION_(?:APP_ID|SECRET)"),
    "OpenAI-style secret": re.compile(r"(?<![A-Za-z0-9_-])sk-[A-Za-z0-9_-]{20,}"),
}


def tracked_files() -> list[str]:
    completed = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return [item for item in completed.stdout.decode("utf-8").split("\0") if item]


def repository_violations(paths: list[str]) -> list[str]:
    violations: list[str] = []
    for path in paths:
        if path in FORBIDDEN_EXACT:
            violations.append(f"forbidden tracked file: {path}")
        if path.startswith(FORBIDDEN_PREFIXES):
            violations.append(f"forbidden tracked runtime/generated path: {path}")
        if path.endswith(FORBIDDEN_SUFFIXES):
            violations.append(f"forbidden generated artifact: {path}")
        if FORBIDDEN_SEGMENTS.intersection(Path(path).parts):
            violations.append(f"forbidden generated directory: {path}")
    return violations


def credential_violations(paths: list[str]) -> list[str]:
    violations: list[str] = []
    for relative_path in paths:
        if not relative_path.startswith(ACTIVE_TEXT_PREFIXES):
            continue
        if "/tests/" in relative_path or relative_path.startswith("scripts/legacy/"):
            continue
        path = ROOT / relative_path
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(content):
                violations.append(f"{label}: {relative_path}")
    return violations


def main() -> int:
    paths = tracked_files()
    violations = repository_violations(paths) + credential_violations(paths)
    if violations:
        print("Repository hygiene check failed:")
        for violation in violations:
            print(f"- {violation}")
        return 1
    print(f"Repository hygiene check passed ({len(paths)} tracked files checked).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
