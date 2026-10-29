from dataclasses import dataclass
import logging
from pathlib import Path


logger = logging.getLogger(__name__)


class ExtractionError(ValueError):
    """Raised when a supported document cannot be extracted safely."""


@dataclass(frozen=True)
class ExtractedPage:
    text: str
    page_number: int | None = None


class DocumentExtractionService:
    """Extract text from supported local document files without OCR."""

    SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt"}

    def extract(self, file_path: str | Path, *, filename: str | None = None, content_type: str | None = None) -> list[ExtractedPage]:
        path = Path(file_path)
        source_name = filename or path.name
        extension = Path(source_name).suffix.lower()
        if extension not in self.SUPPORTED_EXTENSIONS:
            raise ExtractionError(f"Unsupported document type: {extension or 'unknown'}")
        if not path.is_file():
            raise ExtractionError("Document file does not exist")
        if path.stat().st_size == 0:
            raise ExtractionError("Document file is empty")

        if extension == ".pdf":
            return self._extract_pdf(path)
        if extension == ".docx":
            return self._extract_docx(path)
        return self._extract_txt(path)

    @staticmethod
    def _extract_pdf(path: Path) -> list[ExtractedPage]:
        try:
            import fitz
        except ImportError as error:
            raise ExtractionError("PyMuPDF is required for PDF extraction") from error
        try:
            with fitz.open(path) as document:
                return [ExtractedPage(page.get_text("text"), index + 1) for index, page in enumerate(document)]
        except Exception as error:
            raise ExtractionError("Could not read PDF document") from error

    @staticmethod
    def _extract_docx(path: Path) -> list[ExtractedPage]:
        try:
            from docx import Document
        except ImportError as error:
            raise ExtractionError("python-docx is required for DOCX extraction") from error
        try:
            document = Document(path)
            text = "\n".join(paragraph.text for paragraph in document.paragraphs)
            return [ExtractedPage(text)]
        except Exception as error:
            raise ExtractionError("Could not read DOCX document") from error

    @staticmethod
    def _extract_txt(path: Path) -> list[ExtractedPage]:
        try:
            return [ExtractedPage(path.read_text(encoding="utf-8"))]
        except UnicodeDecodeError as error:
            logger.warning("Text extraction rejected invalid UTF-8 input (%s)", type(error).__name__)
            raise ExtractionError("Text document is not valid UTF-8") from error
        except OSError as error:
            logger.warning("Text extraction failed during file read (%s)", type(error).__name__)
            raise ExtractionError("Could not read text document") from error


def has_extractable_text(pages: list[ExtractedPage]) -> bool:
    return any(page.text.strip() for page in pages)
