from pathlib import Path

from backend.core.settings import Settings
from backend.services.file_service import FileService


def test_extract_text_supports_markdown(tmp_path: Path) -> None:
    settings = Settings(storage_dir=tmp_path / "storage")
    service = FileService(settings)
    sample = tmp_path / "sample.md"
    sample.write_text("# 标题\n\n第一条 处理目的\n乙方仅可基于约定目的处理个人信息。", encoding="utf-8")

    extracted = service.extract_text(sample)

    assert "第一条 处理目的" in extracted
    assert "个人信息" in extracted
