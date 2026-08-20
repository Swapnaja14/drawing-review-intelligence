"""
src/controllers/app_controller.py
Application Controller & Thread-Safe Background Workers for Desktop UI.
Orchestrates Auth, PDF Operations, File Service, and Processing Workflow Engine.
"""

from pathlib import Path
from typing import Optional
from PySide6.QtCore import QObject, QThread, Signal

from src.services.pdf_service import PDFService
from src.services.auth_service import AuthService
from src.services.file_service import FileService
from src.services.workflow_engine import ProcessingWorkflowEngine
from src.infrastructure.pdf.pymupdf_adapter import PyMuPDFAdapter
from src.infrastructure.storage.repository import DatabaseEngine, DrawingRepository, ProjectRepository
from src.core.dtos.pdf_dtos import PDFDocumentDTO, RenderedPageDTO
from src.core.dtos.auth_dtos import UserDTO, SessionTokenDTO
from src.core.dtos.workflow_dtos import WorkflowStepDTO, WorkflowResultDTO, FileValidationResultDTO
from src.core.exceptions.auth_exceptions import InvalidCredentialsError
from src.infrastructure.logging.logger import get_logger

logger = get_logger("AppController")


class WorkflowWorker(QThread):
    """Background QThread executing full multi-step drawing processing pipeline without freezing UI."""

    step_signal = Signal(object)      # Emits WorkflowStepDTO
    completed_signal = Signal(object) # Emits WorkflowResultDTO
    error_signal = Signal(str)        # Emits error string

    def __init__(self, workflow_engine: ProcessingWorkflowEngine, file_path: Path):
        super().__init__()
        self.workflow_engine = workflow_engine
        self.file_path = file_path

    def run(self):
        try:
            def on_progress(step_snapshot: WorkflowStepDTO):
                self.step_signal.emit(step_snapshot)

            result = self.workflow_engine.execute_workflow(self.file_path, progress_callback=on_progress)
            self.completed_signal.emit(result)
        except Exception as e:
            logger.error(f"Error in WorkflowWorker: {e}")
            self.error_signal.emit(str(e))


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

    # Workflow Signals
    workflow_step_signal = Signal(object)      # WorkflowStepDTO
    workflow_completed_signal = Signal(object) # WorkflowResultDTO

    # Auth Controller Signals
    user_signed_in_signal = Signal(object)    # SessionTokenDTO
    user_signed_out_signal = Signal()
    auth_error_signal = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.pdf_adapter = PyMuPDFAdapter()
        self.pdf_service = PDFService(pdf_loader=self.pdf_adapter)
        self.file_service = FileService()
        self.db_engine = DatabaseEngine()
        self.drawing_repo = DrawingRepository(self.db_engine)
        self.project_repo = ProjectRepository(self.db_engine)
        self.auth_service = AuthService(self.db_engine)
        self.workflow_engine = ProcessingWorkflowEngine(
            file_service=self.file_service,
            pdf_service=self.pdf_service,
            drawing_repo=self.drawing_repo
        )

        self._active_doc: Optional[PDFDocumentDTO] = None
        self._current_session: Optional[SessionTokenDTO] = None
        self._load_worker: Optional[PDFLoadWorker] = None
        self._render_worker: Optional[PDFRenderWorker] = None
        self._workflow_worker: Optional[WorkflowWorker] = None

    @property
    def current_document(self) -> Optional[PDFDocumentDTO]:
        return self._active_doc

    @property
    def current_user(self) -> Optional[UserDTO]:
        return self._current_session.user if self._current_session else None

    # ── Workflow Pipeline API ───────────────────────────────────────

    def validate_file(self, file_path: str | Path) -> FileValidationResultDTO:
        """Validates an uploaded PDF drawing file."""
        return self.file_service.validate_pdf_file(file_path)

    def start_processing_workflow(self, file_path: str | Path) -> None:
        """Triggers non-blocking background multi-step workflow execution."""
        path = Path(file_path).resolve()
        logger.info(f"AppController launching workflow pipeline for: {path.name}")

        if self._workflow_worker and self._workflow_worker.isRunning():
            self._workflow_worker.terminate()
            self._workflow_worker.wait()

        self._workflow_worker = WorkflowWorker(self.workflow_engine, path)
        self._workflow_worker.step_signal.connect(self._on_workflow_step)
        self._workflow_worker.completed_signal.connect(self._on_workflow_completed)
        self._workflow_worker.error_signal.connect(self._on_doc_error)
        self._workflow_worker.start()

    def _on_workflow_step(self, step_snapshot: WorkflowStepDTO):
        self.workflow_step_signal.emit(step_snapshot)

    def _on_workflow_completed(self, result_dto: WorkflowResultDTO):
        logger.info(f"AppController: Workflow finished for '{result_dto.file_name}'.")
        self.workflow_completed_signal.emit(result_dto)
        # Also auto-load document for viewer
        if self.file_service:
            path = Path(self._workflow_worker.file_path) if self._workflow_worker else None
            if path and path.exists():
                doc_dto = self.pdf_service.process_pdf_document(path)
                self._active_doc = doc_dto
                self.document_loaded_signal.emit(doc_dto)

    # ── Authentication API ──────────────────────────────────────────

    def sign_in(self, username_or_email: str, password: str) -> bool:
        try:
            session_dto = self.auth_service.authenticate_user(username_or_email, password)
            self._current_session = session_dto
            logger.info(f"AppController: User '{session_dto.user.username}' logged in.")
            self.user_signed_in_signal.emit(session_dto)
            return True
        except InvalidCredentialsError as e:
            err_msg = str(e)
            logger.warning(f"Sign in failed: {err_msg}")
            self.auth_error_signal.emit(err_msg)
            return False
        except Exception as e:
            err_msg = f"Unexpected sign in error: {e}"
            logger.error(err_msg)
            self.auth_error_signal.emit(err_msg)
            return False

    def sign_out(self) -> bool:
        if self._current_session:
            self.auth_service.sign_out(self._current_session.token)
            user_name = self._current_session.user.username
            self._current_session = None
            logger.info(f"AppController: User '{user_name}' signed out.")
            self.user_signed_out_signal.emit()
            return True
        return False

    # ── PDF Operations ──────────────────────────────────────────────

    def load_pdf_file(self, file_path: str | Path) -> None:
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
