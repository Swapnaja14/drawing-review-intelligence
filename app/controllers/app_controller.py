"""
src/controllers/app_controller.py
Application Controller & Thread-Safe Background Workers for Desktop UI.
"""

from pathlib import Path
from typing import Optional
from PySide6.QtCore import QObject, QThread, Signal

from src.services.pdf_service import PDFService
from src.infrastructure.pdf.pymupdf_adapter import PyMuPDFAdapter
from src.infrastructure.storage.repository import DatabaseEngine, DrawingRepository, ProjectRepository
from src.core.dtos.pdf_dtos import PDFDocumentDTO, RenderedPageDTO
from src.infrastructure.logging.logger import get_logger

logger = get_logger("AppController")


class PDFLoadWorker(QThread):
    """Worker thread for loading PDF document & extracting metadata without blocking GUI."""

    success_signal = Signal(object)  # Emits PDFDocumentDTO
    error_signal = Signal(str)      # Emits error string

    def __init__(self, pdf_service: PDFService, drawing_repo: DrawingRepository, file_path: Path):
        super().__init__()
        self.pdf_service = pdf_service
        self.drawing_repo = drawing_repo
        self.file_path = file_path

    def run(self):
        try:
            doc_dto = self.pdf_service.process_pdf_document(self.file_path)
            # Save drawing metadata to database
            try:
                self.drawing_repo.save_drawing_from_dto(doc_dto)
            except Exception as e:
                logger.warning(f"Database save warning: {e}")
            self.success_signal.emit(doc_dto)
        except Exception as e:
            logger.error(f"Error in PDFLoadWorker: {e}")
            self.error_signal.emit(str(e))


class PDFRenderWorker(QThread):
    """Worker thread for high-DPI page rendering without blocking GUI."""

    rendered_signal = Signal(object)  # Emits RenderedPageDTO
    error_signal = Signal(str)

    def __init__(self, pdf_service: PDFService, file_path: Path, page_number: int, dpi: int = 300):
        super().__init__()
        self.pdf_service = pdf_service
        self.file_path = file_path
        self.page_number = page_number
        self.dpi = dpi

    def run(self):
        try:
            rendered_dto = self.pdf_service.get_page_render(self.file_path, self.page_number, self.dpi)
            self.rendered_signal.emit(rendered_dto)
        except Exception as e:
            logger.error(f"Error in PDFRenderWorker rendering page {self.page_number}: {e}")
            self.error_signal.emit(str(e))


class AppController(QObject):
    """
    Central Application Controller mediating between PySide6 GUI views
    and backend services / database repositories.
    """

    # Global Controller Signals
    document_loaded_signal = Signal(object)   # PDFDocumentDTO
    page_rendered_signal = Signal(object)     # RenderedPageDTO
    processing_error_signal = Signal(str)     # Error string

    def __init__(self, parent=None):
        super().__init__(parent)
        self.pdf_adapter = PyMuPDFAdapter()
        self.pdf_service = PDFService(pdf_loader=self.pdf_adapter)
        self.db_engine = DatabaseEngine()
        self.drawing_repo = DrawingRepository(self.db_engine)
        self.project_repo = ProjectRepository(self.db_engine)

        self._active_doc: Optional[PDFDocumentDTO] = None
        self._load_worker: Optional[PDFLoadWorker] = None
        self._render_worker: Optional[PDFRenderWorker] = None

    @property
    def current_document(self) -> Optional[PDFDocumentDTO]:
        return self._active_doc

    def load_pdf_file(self, file_path: str | Path) -> None:
        """Triggers non-blocking background loading of a PDF drawing."""
        path = Path(file_path).resolve()
        logger.info(f"AppController load request for: {path}")

        if self._load_worker and self._load_worker.isRunning():
            self._load_worker.terminate()
            self._load_worker.wait()

        self._load_worker = PDFLoadWorker(self.pdf_service, self.drawing_repo, path)
        self._load_worker.success_signal.connect(self._on_doc_loaded)
        self._load_worker.error_signal.connect(self._on_doc_error)
        self._load_worker.start()

    def request_page_render(self, file_path: str | Path, page_number: int, dpi: int = 300) -> None:
        """Triggers non-blocking background rendering of a PDF page at target DPI."""
        path = Path(file_path).resolve()

        if self._render_worker and self._render_worker.isRunning():
            self._render_worker.terminate()
            self._render_worker.wait()

        self._render_worker = PDFRenderWorker(self.pdf_service, path, page_number, dpi)
        self._render_worker.rendered_signal.connect(self._on_page_rendered)
        self._render_worker.error_signal.connect(self._on_render_error)
        self._render_worker.start()

    def _on_doc_loaded(self, doc_dto: PDFDocumentDTO) -> None:
        self._active_doc = doc_dto
        logger.info(f"AppController: Document '{doc_dto.file_name}' ready with {doc_dto.total_pages} pages.")
        self.document_loaded_signal.emit(doc_dto)

    def _on_doc_error(self, err_msg: str) -> None:
        logger.error(f"AppController document error: {err_msg}")
        self.processing_error_signal.emit(err_msg)

    def _on_page_rendered(self, rendered_dto: RenderedPageDTO) -> None:
        self.page_rendered_signal.emit(rendered_dto)

    def _on_render_error(self, err_msg: str) -> None:
        logger.error(f"AppController render error: {err_msg}")
        self.processing_error_signal.emit(err_msg)

    def get_dashboard_kpis(self):
        return self.project_repo.get_kpis()

    def get_all_projects(self):
        return self.project_repo.get_all_projects()
