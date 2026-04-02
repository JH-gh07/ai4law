from backend.models.review import UploadedFileModel


class DocumentParser:
    def parse(self, uploaded_file: UploadedFileModel) -> dict:
        return {
            "file_id": uploaded_file.id,
            "filename": uploaded_file.filename,
            "text": uploaded_file.extracted_text,
            "content_type": uploaded_file.content_type,
        }
