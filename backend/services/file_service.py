from pathlib import Path
from uuid import uuid4

from docx import Document
from fastapi import HTTPException, UploadFile
from pypdf import PdfReader

from backend.core.settings import Settings


class FileService:
    allowed_extensions = {".pdf", ".docx", ".txt", ".md", ".json", ".csv"}

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def save_upload(self, task_id: str, upload: UploadFile) -> Path:
        ext = Path(upload.filename or "").suffix.lower()
        if ext not in self.allowed_extensions:
            raise HTTPException(status_code=400, detail="Unsupported file type")

        destination = self.settings.upload_dir / task_id
        destination.mkdir(parents=True, exist_ok=True)
        filename = f"{uuid4()}{ext}"
        path = destination / filename
        with path.open("wb") as buffer:
            buffer.write(upload.file.read())
        return path

    def extract_text(self, path: Path) -> str:
        ext = path.suffix.lower()
        if ext == ".docx":
            return self._extract_docx(path)
        if ext == ".pdf":
            return self._extract_pdf(path)
        if ext in {".txt", ".md", ".json", ".csv"}:
            return self._extract_plain_text(path)
        raise HTTPException(status_code=400, detail="Unsupported file type")

    def _extract_docx(self, path: Path) -> str:
        document = Document(path)
        return "\n".join(paragraph.text for paragraph in document.paragraphs if paragraph.text.strip())

    def _extract_pdf(self, path: Path) -> str:
        reader = PdfReader(str(path))
        chunks: list[str] = []
        for page in reader.pages:
            text = page.extract_text() or ""
            chunks.append(text)
        extracted = "\n".join(chunks).strip()
        if not extracted:
            raise HTTPException(status_code=400, detail="PDF text extraction failed; scanned OCR PDFs are not supported in MVP")
        return extracted

    def _extract_plain_text(self, path: Path) -> str:
        extracted = path.read_text(encoding="utf-8", errors="ignore").strip()
        if not extracted:
            raise HTTPException(status_code=400, detail="Plain text extraction failed; file is empty")
        return extracted
