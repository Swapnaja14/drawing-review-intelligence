"""
app/controllers/app_controller.py
Application Controller & Thread-Safe Background Workers for Desktop UI.

ARCHITECTURE NOTE:
AppController is the single access point between the PySide6 UI layer and all
backend services and database repositories. UI screens must NEVER instantiate
repositories or services directly.

Data flow:
    UI Screen → AppController → Repository → SQLAlchemy → SQLite

The controller owns two important state properties after a PDF is loaded:
    current_document   → PDFDocumentDTO  (PDF metadata, page dimensions)
    current_drawing_id → str             (DrawingModel.id, e.g. "DWG-XXXXXXXX")

INTEGRATION WARNING:
    PDF filename (current_document.file_name) is NOT the database drawing ID.
    current_document.file_name = "UCC-E-101.pdf"  (bare filename)
    current_drawing_id          = "DWG-3F7A1C2B"  (DB primary key)
    Always use current_drawing_id when associating comments with a drawing.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QObject, QThread, Signal

from src.services.pdf_service import PDFService
from src.infrastructure.pdf.pymupdf_adapter import PyMuPDFAdapter
from src.infrastructure.storage.repository import (
    DatabaseEngine,
    DrawingRepository,
    ProjectRepository,
    CommentRepository,
)
from src.core.dtos.pdf_dtos import PDFDocumentDTO, RenderedPageDTO
from src.infrastructure.logging.logger import get_logger

# Resolve project root so the DB path is correct regardless of CWD
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_DB_PATH = _PROJECT_ROOT / "data" / "ucc_database.db"

logger = get_logger("AppController")


# ---------------------------------------------------------------------------
# Background workers
# ---------------------------------------------------------------------------

class PDFLoadWorker(QThread):
    """Worker thread: loads a PDF document and saves drawing metadata to DB.

    Emits success_signal(PDFDocumentDTO, drawing_id: str) on completion so
    AppController can store current_drawing_id without blocking the UI thread.

    INTEGRATION NOTE:
    The drawing_id emitted here is the DrawingModel.id primary key returned by
    DrawingRepository.save_drawing_from_dto(). It is NOT the PDF filename.
    AppController stores this as _current_drawing_id for use by all downstream
    comment operations.
    """

    # Emits (doc_dto, drawing_id) — drawing_id may be "" on DB save failure
    success_signal = Signal(object, str)
    error_signal   = Signal(str)

    def __init__(
        self,
        pdf_service: PDFService,
        drawing_repo: DrawingRepository,
        file_path: Path,
    ) -> None:
        super().__init__()
        self.pdf_service  = pdf_service
        self.drawing_repo = drawing_repo
        self.file_path    = file_path

    def run(self) -> None:
        try:
            doc_dto = self.pdf_service.process_pdf_document(self.file_path)

            drawing_id = ""
            try:
                result = self.drawing_repo.save_drawing_from_dto(doc_dto)
                drawing_id = result.get("id", "")
            except Exception as exc:
                logger.warning(f"Database save warning: {exc}")

            self.success_signal.emit(doc_dto, drawing_id)

        except Exception as exc:
            logger.error(f"Error in PDFLoadWorker: {exc}")
            self.error_signal.emit(str(exc))


class PDFRenderWorker(QThread):
    """Worker thread for high-DPI page rendering without blocking GUI."""

    rendered_signal = Signal(object)   # RenderedPageDTO
    error_signal    = Signal(str)

    def __init__(
        self,
        pdf_service: PDFService,
        file_path: Path,
        page_number: int,
        dpi: int = 300,
    ) -> None:
        super().__init__()
        self.pdf_service  = pdf_service
        self.file_path    = file_path
        self.page_number  = page_number
        self.dpi          = dpi

    def run(self) -> None:
        try:
            rendered_dto = self.pdf_service.get_page_render(
                self.file_path, self.page_number, self.dpi
            )
            self.rendered_signal.emit(rendered_dto)
        except Exception as exc:
            logger.error(
                f"Error in PDFRenderWorker rendering page {self.page_number}: {exc}"
            )
            self.error_signal.emit(str(exc))


# ---------------------------------------------------------------------------
# AppController
# ---------------------------------------------------------------------------

class AppController(QObject):
    """
    Central application controller — mediates between PySide6 UI and all
    backend services / database repositories.

    ARCHITECTURE NOTE:
    All database access from the UI must go through this controller.
    UI screens must NOT import or instantiate any repository class directly.
    Repositories are private implementation details of the controller.

    Signals
    -------
    document_loaded_signal : PDFDocumentDTO
        Emitted (on the main thread) when a PDF has been fully loaded and
        its drawing record saved to the database.
    page_rendered_signal   : RenderedPageDTO
        Emitted when a background page-render completes.
    processing_error_signal : str
        Emitted on any background worker error.
    """

    document_loaded_signal  = Signal(object)   # PDFDocumentDTO
    page_rendered_signal    = Signal(object)   # RenderedPageDTO
    processing_error_signal = Signal(str)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)

        # ── Services ──────────────────────────────────────────────
        self.pdf_adapter = PyMuPDFAdapter()
        self.pdf_service = PDFService(pdf_loader=self.pdf_adapter)

        # ── Database ──────────────────────────────────────────────
        self.db_engine    = DatabaseEngine(db_path=_DB_PATH)
        self.drawing_repo = DrawingRepository(self.db_engine)
        self.project_repo = ProjectRepository(self.db_engine)
        self.comment_repo = CommentRepository(self.db_engine)

        # ── In-session state ──────────────────────────────────────
        self._active_doc: Optional[PDFDocumentDTO] = None
        # INTEGRATION NOTE:
        # _current_drawing_id is the DrawingModel.id PK for the currently
        # loaded drawing. It is NOT the PDF filename. Always use this value
        # when querying or saving comments for the active drawing.
        # Value is "" (empty string) when no PDF has been loaded this session.
        self._current_drawing_id: str = ""

        # ── Worker references ─────────────────────────────────────
        self._load_worker:   Optional[PDFLoadWorker]   = None
        self._render_worker: Optional[PDFRenderWorker] = None

    # ── Properties ────────────────────────────────────────────────

    @property
    def current_document(self) -> Optional[PDFDocumentDTO]:
        """The PDFDocumentDTO for the currently loaded drawing, or None."""
        return self._active_doc

    @property
    def current_drawing_id(self) -> str:
        """
        The DrawingModel.id primary key for the currently loaded drawing.

        Returns "" if no drawing has been loaded in this session.

        INTEGRATION NOTE:
        This value is set after a successful PDF load and DB save in
        PDFLoadWorker.run(). It is the only authoritative drawing ID for
        comment operations. Do NOT substitute PDF filename for this value.
        """
        return self._current_drawing_id

    # ── PDF operations ────────────────────────────────────────────

    def load_pdf_file(self, file_path: str | Path) -> None:
        """Trigger non-blocking background loading of a PDF drawing."""
        path = Path(file_path).resolve()
        logger.info(f"AppController load request for: {path}")

        if self._load_worker and self._load_worker.isRunning():
            self._load_worker.terminate()
            self._load_worker.wait()

        self._load_worker = PDFLoadWorker(self.pdf_service, self.drawing_repo, path)
        self._load_worker.success_signal.connect(self._on_doc_loaded)
        self._load_worker.error_signal.connect(self._on_doc_error)
        self._load_worker.start()

    def request_page_render(
        self, file_path: str | Path, page_number: int, dpi: int = 300
    ) -> None:
        """Trigger non-blocking background rendering of a PDF page at target DPI."""
        path = Path(file_path).resolve()

        if self._render_worker and self._render_worker.isRunning():
            self._render_worker.terminate()
            self._render_worker.wait()

        self._render_worker = PDFRenderWorker(self.pdf_service, path, page_number, dpi)
        self._render_worker.rendered_signal.connect(self._on_page_rendered)
        self._render_worker.error_signal.connect(self._on_render_error)
        self._render_worker.start()

    # ── Project / dashboard operations ────────────────────────────

    def get_dashboard_kpis(self) -> Dict[str, Any]:
        """Return live KPI aggregates from the database."""
        return self.project_repo.get_kpis()

    def get_all_projects(self) -> List[Dict[str, Any]]:
        """Return all project records from the database."""
        return self.project_repo.get_all_projects()

    # ── Comment operations ─────────────────────────────────────────────────
    #
    # These methods are the ONLY way UI screens should access comment data.
    # Screens must never instantiate CommentRepository themselves.

    def get_comments_for_drawing(
        self, drawing_id: str
    ) -> List[Dict[str, Any]]:
        """
        Return all normalised comment display dicts for the given drawing.

        Parameters
        ----------
        drawing_id:
            The DrawingModel.id ("DWG-XXXXXXXX"). Use current_drawing_id.

        Returns
        -------
        List of normalised comment dicts (see normalise_comment for keys).
        Returns [] if drawing_id is empty or no comments exist.
        """
        if not drawing_id:
            return []
        raw = self.comment_repo.get_comments_for_drawing(drawing_id)
        return [self.normalise_comment(c) for c in raw]

    def update_comment_status(
        self, comment_id: str, status: str, verified_by_human: bool = True
    ) -> None:
        """
        Persist a status change for a single comment.

        Parameters
        ----------
        comment_id : str
            The CommentModel primary key ("CMT-XXXXXXXX").
        status : str
            One of: "Pending", "Approved", "Rejected", "Flagged".
        verified_by_human : bool
            True when the change comes from a human reviewer action.

        INTEGRATION NOTE:
        Status vocabulary is fixed. Do not pass arbitrary strings.
        Permitted values: "Pending", "Approved", "Rejected", "Flagged".
        """
        self.comment_repo.update_comment_status(
            comment_id, status, verified_by_human
        )

    def update_comment_text(self, comment_id: str, new_text: str) -> None:
        """
        Persist a corrected OCR text for a single comment.

        Called from the review screen (edit/save action) and the OCR
        results screen (inline text edit).
        """
        self.comment_repo.update_comment_text(comment_id, new_text)

    def get_category_counts(
        self, drawing_id: Optional[str] = None
    ) -> Dict[str, int]:
        """
        Return comment counts grouped by category name.

        Parameters
        ----------
        drawing_id:
            If provided, scoped to that drawing.
            If None, aggregates across all drawings (used by analytics).

        Returns
        -------
        Dict[str, int] e.g. {"Dimensional": 42, "Structural": 18}
        """
        return self.comment_repo.get_category_counts(drawing_id)

    # ── Data normalisation ─────────────────────────────────────────────────

    def normalise_comment(self, db_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert a raw CommentRepository dict to the normalised display shape
        used by all UI screens.

        This is the single mapping point between the database representation
        and the UI representation of a comment. All field-name differences
        are resolved here — they must NOT be scattered through UI files.

        DB dict keys → display dict keys:
            "raw_text"     → "ocr_text"
            "page_number"  → "page"
            "category_name"→ "category"
            "user_id"      → "reviewer"
            "created_at"   → "timestamp"
            "id"           → "id"         (unchanged)
            "drawing_id"   → "drawing_id" (unchanged)
            "confidence"   → "confidence" (unchanged)
            "status"       → "status"     (unchanged)

        BBox conversion:
            DB stores (bbox_x0, bbox_y0, bbox_x1, bbox_y1) as absolute PDF
            point coordinates inside the "bbox" tuple.
            This method returns bbox as a normalised (x, y, w, h) tuple in
            range 0–1 IF page dimensions are available from current_document.
            Otherwise returns the raw (x0, y0, x1, y1) tuple unchanged.

            INTEGRATION WARNING:
            The comment_viewer_screen must check whether bbox is normalised
            or absolute. If current_document is None when a drawing is loaded
            from a previous session, normalisation cannot be performed without
            an additional PageModel query. See comment_viewer_screen.py for
            the handling strategy.

        drawing_no:
            Derived from the drawing's file_name (stripped of extension) as a
            human-readable label. Requires current_document to be set.
            Falls back to drawing_id if not available.
        """
        raw_bbox = db_dict.get("bbox", (0.0, 0.0, 0.0, 0.0))
        normalised_bbox = raw_bbox  # default: pass through unchanged

        # Attempt normalisation using in-session page dimension data
        doc = self._active_doc
        if doc is not None and len(doc.pages) > 0:
            page_num = db_dict.get("page_number", 1)
            # pages list is 0-indexed; page_number is 1-indexed
            idx = max(0, min(page_num - 1, len(doc.pages) - 1))
            page_meta = doc.pages[idx]
            w_pt = page_meta.width_pt
            h_pt = page_meta.height_pt
            if w_pt > 0 and h_pt > 0:
                x0, y0, x1, y1 = raw_bbox
                normalised_bbox = (
                    x0 / w_pt,
                    y0 / h_pt,
                    (x1 - x0) / w_pt,
                    (y1 - y0) / h_pt,
                )

        # Derive a human-readable drawing number from the file name
        drawing_no = db_dict.get("drawing_id", "")
        if doc is not None:
            drawing_no = doc.file_name.rsplit(".", 1)[0]  # strip extension

        return {
            "id":          db_dict.get("id", ""),
            "drawing_id":  db_dict.get("drawing_id", ""),
            "drawing_no":  drawing_no,
            "page":        db_dict.get("page_number", 1),
            "ocr_text":    db_dict.get("raw_text", ""),
            "category":    db_dict.get("category_name") or "Uncategorized",
            "confidence":  db_dict.get("confidence", 0.0),
            "status":      db_dict.get("status", "Pending"),
            "bbox":        normalised_bbox,
            "reviewer":    db_dict.get("user_id"),   # FK; UI shows None or resolves separately
            "timestamp":   db_dict.get("created_at", ""),
            "is_verified": db_dict.get("is_verified_by_human", False),
        }

    # ── Internal slots ────────────────────────────────────────────

    def _on_doc_loaded(self, doc_dto: PDFDocumentDTO, drawing_id: str) -> None:
        self._active_doc = doc_dto
        self._current_drawing_id = drawing_id
        logger.info(
            f"AppController: '{doc_dto.file_name}' ready. "
            f"drawing_id='{drawing_id}', pages={doc_dto.total_pages}"
        )
        # Emit only the DTO — external consumers (MainWindow, PdfViewerPage)
        # do not need the drawing_id and their signatures are unchanged.
        self.document_loaded_signal.emit(doc_dto)

    def _on_doc_error(self, err_msg: str) -> None:
        logger.error(f"AppController document error: {err_msg}")
        self.processing_error_signal.emit(err_msg)

    def _on_page_rendered(self, rendered_dto: RenderedPageDTO) -> None:
        self.page_rendered_signal.emit(rendered_dto)

    def _on_render_error(self, err_msg: str) -> None:
        logger.error(f"AppController render error: {err_msg}")
        self.processing_error_signal.emit(err_msg)
