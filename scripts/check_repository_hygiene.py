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
}
ALLOWED_STORAGE_FILES = {
    "storage/README.md",
    "storage/runtime_settings.example.json",
}
FORBIDDEN_PREFIXES = (
    ".vite/",
    ".superpowers/",
    "ai_engine/",
    "doc/",
    "backend/modules/cpra/",
    "backend/modules/us_14117/",
    "backend/modules/eu_scc/",
    "backend/modules/bcr/",
    "backend/modules/dpia/",
    "backend/modules/tia/",
    "backend/modules/assessment/",
    "backend/modules/pipia/",
    "backend/modules/scc/",
    "backend/modules/diagnosis/",
    "backend/modules/cn_flow/",
    "backend/modules/v0_task_gateway/",
    "backend/modules/",
    "frontend/.codex-archives/",
    "frontend/storage/",
    "frontend/tmp/",
)
FORBIDDEN_SEGMENTS = {"__pycache__", "node_modules", ".pytest_cache", ".vite"}
FORBIDDEN_SUFFIXES = (".pyc", ".pyo", ".tsbuildinfo", ".bak")
ACTIVE_TEXT_PREFIXES = ("backend/", "config/", "frontend/src/", "scripts/")
FORBIDDEN_ACTIVE_PATH_LITERALS = (
    "doc/",
    "backend.modules.cpra",
    "backend.modules.us_14117",
    "backend.modules.eu_scc",
    "backend.modules.bcr",
    "backend.modules.dpia",
    "backend.modules.tia",
    "backend.modules.assessment",
    "backend.modules.pipia",
    "backend.modules.scc",
    "backend.modules.diagnosis",
    "backend.modules.cn_flow",
    "backend.modules.v0_task_gateway",
    "backend.modules.",
)
SECRET_PATTERNS = {
    "embedded competition credential": re.compile(r"DELILEGAL_COMPETITION_(?:APP_ID|SECRET)"),
    "OpenAI-style secret": re.compile(r"(?<![A-Za-z0-9_-])sk-[A-Za-z0-9_-]{20,}"),
}


def repository_files() -> list[str]:
    completed = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return [
        item
        for item in completed.stdout.decode("utf-8").split("\0")
        if item and (ROOT / item).is_file()
    ]


def repository_violations(paths: list[str]) -> list[str]:
    violations: list[str] = []
    for path in paths:
        if path.startswith("storage/") and path not in ALLOWED_STORAGE_FILES:
            violations.append(f"forbidden tracked runtime storage: {path}")
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
        if "/tests/" in relative_path:
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


def active_path_violations(paths: list[str]) -> list[str]:
    violations: list[str] = []
    for relative_path in paths:
        if not relative_path.startswith(ACTIVE_TEXT_PREFIXES):
            continue
        if (
            "/tests/" in relative_path
            or relative_path == "scripts/check_repository_hygiene.py"
            or relative_path == "config/local_new_parity_manifest.json"
        ):
            continue
        path = ROOT / relative_path
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for literal in FORBIDDEN_ACTIVE_PATH_LITERALS:
            if literal in content:
                violations.append(f"legacy active path {literal}: {relative_path}")
    return violations

def main() -> int:
    paths = repository_files()
    violations = (
        repository_violations(paths)
        + credential_violations(paths)
        + active_path_violations(paths)
    )
    if violations:
        print("Repository hygiene check failed:")
        for violation in violations:
            print(f"- {violation}")
        return 1
    print(f"Repository hygiene check passed ({len(paths)} repository files checked).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
