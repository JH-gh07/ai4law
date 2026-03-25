from pathlib import Path


class FileParser:
    SUPPORTED_SUFFIXES = {".txt", ".md", ".json", ".csv"}

    def parse_text(self, file_path: str) -> str:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        if path.suffix.lower() not in self.SUPPORTED_SUFFIXES:
            raise ValueError(
                "Unsupported file type in v0. Supported: txt, md, json, csv. "
                "For pdf/docx parsing integrate dedicated parser in next iteration."
            )
        return path.read_text(encoding="utf-8", errors="ignore")
