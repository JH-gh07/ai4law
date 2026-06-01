from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from typing import Optional

from backend.core.settings import get_settings


class KnowledgeStorageManager:
    """Manages file storage for the regulatory knowledge base.

    - SHA-256 hash deduplication
    - Organised directory layout: storage/knowledge/raw/{jurisdiction}/{doc_type}/
    - Keeps original filename with hash prefix to avoid collisions.
    """

    def __init__(self, base_dir: str | None = None) -> None:
        if base_dir is None:
            settings = get_settings()
            base_dir = str(Path(settings.storage_dir) / "knowledge")
        self.base_dir = Path(base_dir)
        self.raw_dir = self.base_dir / "raw"

    @staticmethod
    def hash_bytes(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    def storage_path(
        self,
        jurisdiction: str,
        doc_type: str,
        file_hash: str,
        original_name: str,
        source: str = "regulatory",
        user_id: str = "",
    ) -> Path:
        if source == "user" and user_id:
            folder = self.raw_dir / "user" / user_id
        else:
            folder = self.raw_dir / jurisdiction / doc_type
        folder.mkdir(parents=True, exist_ok=True)
        stem = Path(original_name).stem
        suffix = Path(original_name).suffix
        return folder / f"{file_hash[:8]}_{stem}{suffix}"

    def exists(self, file_hash: str) -> bool:
        """Check if a file with this hash already exists by scanning the raw dir."""
        candidates = list(self.raw_dir.rglob(f"{file_hash[:8]}_*"))
        for candidate in candidates:
            if candidate.is_file():
                try:
                    existing_hash = self.hash_bytes(candidate.read_bytes())
                    if existing_hash == file_hash:
                        return True
                except OSError:
                    continue
        return False

    def save(self, file_bytes: bytes, original_name: str, *,
             jurisdiction: str = "cn", doc_type: str = "law",
             source: str = "regulatory", user_id: str = "") -> tuple[str, Path, bool]:
        """Save a file; returns (hash, path, is_duplicate)."""
        file_hash = self.hash_bytes(file_bytes)
        dest = self.storage_path(jurisdiction, doc_type, file_hash, original_name, source, user_id)

        if dest.exists():
            try:
                existing_hash = self.hash_bytes(dest.read_bytes())
                if existing_hash == file_hash:
                    return file_hash, dest, True
            except OSError:
                pass

        dest.write_bytes(file_bytes)
        return file_hash, dest, False

    def read(self, file_hash: str) -> Optional[bytes]:
        candidates = list(self.raw_dir.rglob(f"{file_hash[:8]}_*"))
        for candidate in candidates:
            if candidate.is_file():
                return candidate.read_bytes()
        return None

    def delete(self, file_hash: str) -> bool:
        candidates = list(self.raw_dir.rglob(f"{file_hash[:8]}_*"))
        deleted = False
        for candidate in candidates:
            if candidate.is_file():
                candidate.unlink()
                deleted = True
        return deleted
