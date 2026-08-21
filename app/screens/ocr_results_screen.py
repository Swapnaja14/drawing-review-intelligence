"""
ocr_results_screen.py — OCR Results screen.

Provides:
    OcrResultsPage(QWidget)
        Editable table of OCR-extracted comment text with confidence bars,
        status chips, a search bar, status filter, and pagination controls.

ARCHITECTURE NOTE:
This screen loads comments through AppController.get_comments_for_drawing()
and persists inline text edits through AppController.update_comment_text().

UI code in this file must NOT:
  - import or instantiate CommentRepository directly
  - execute SQLAlchemy queries
  - access SQLite

MOCK DATA FALLBACK:
When no controller is present or the database has no comments for the loaded
drawing, the screen falls back to app/mock_data.py COMMENTS so that the UI
remains functional during development. This fallback is intentional and must
be retained until the OCR/AI pipeline populates the database.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional, Union

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame,
                                QLabel, QTableView, QPushButton, QComboBox,
                                QHeaderView, QAbstractItemView)
from PySide6.QtGui import QFont, QStandardItemModel, QStandardItem
from PySide6.QtCore import Qt, QSortFilterProxyModel

from app import mock_data as md
from app.components.comment_table import ConfidenceDelegate, StatusDelegate
from app.components.search_bar import SearchBar


def _get(c: Union[Dict[str, Any], Any], field: str, default: Any = "") -> Any:
    """Access a field from either a normalised display dict or a mock dataclass."""
    if isinstance(c, dict):
        return c.get(field, default)
    return getattr(c, field, default)


class OcrResultsPage(QWidget):
    """
    OCR Results — editable table with confidence bars, status chips,
    search, filter, and pagination.
    """

    def __init__(self, controller=None, parent=None):
        super().__init__(parent)
        self._controller = controller
        self._page      = 0
        self._page_size = 10

        # Load comments from DB or fall back to mock data
        # INTEGRATION NOTE:
        # DB comments are normalised dicts. Mock data items are dataclass objects.
        # The _get() helper handles both. Once the OCR pipeline populates the DB,
        # the fallback will naturally be bypassed.
        self._comments: List[Any] = self._load_comments()

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        # ── Toolbar ───────────────────────────────────────────────
        tb = QHBoxLayout()
        tb.setSpacing(12)

        search = SearchBar(
            placeholder="  🔍  Search OCR text, drawing number…",
            fixed_width=320,
        )
        tb.addWidget(search)
        tb.addStretch()

        filt = QComboBox()
        filt.addItems(["All Status", "Pending", "Approved", "Rejected", "Flagged"])
        filt.setFixedHeight(36)
        filt.setFixedWidth(160)
        tb.addWidget(filt)

        export_btn = QPushButton("  ↑  Export")
        export_btn.setObjectName("SecondaryBtn")
        export_btn.setFixedHeight(36)
        tb.addWidget(export_btn)

        root.addLayout(tb)

        # ── Table ─────────────────────────────────────────────────
        table_card = QFrame()
        table_card.setObjectName("Card")
        tc_lay = QVBoxLayout(table_card)
        tc_lay.setContentsMargins(0, 0, 0, 0)

        self._model = self._build_model()
        self._proxy = QSortFilterProxyModel()
        self._proxy.setSourceModel(self._model)
        self._proxy.setFilterKeyColumn(-1)
        self._proxy.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        search.search_changed.connect(self._proxy.setFilterFixedString)

        self._table = QTableView()
        self._table.setModel(self._proxy)
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.verticalHeader().hide()
        self._table.setShowGrid(False)
        self._table.setItemDelegateForColumn(2, ConfidenceDelegate(self._table))
        self._table.setItemDelegateForColumn(3, StatusDelegate(self._table))

        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(2, 130)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(3, 120)

        # Connect text edits to persistence
        # INTEGRATION NOTE:
        # When a user double-clicks and edits OCR text, dataChanged fires.
        # _on_text_edited() resolves the comment ID from the ID column and
        # calls AppController.update_comment_text(). For mock data IDs
        # (format "C-NNNN"), persistence is skipped.
        self._model.dataChanged.connect(self._on_text_edited)

        tc_lay.addWidget(self._table)
        root.addWidget(table_card, 1)

        # ── Pagination ────────────────────────────────────────────
        pag = QHBoxLayout()
        pag.setSpacing(8)

        rpp_lbl = QLabel("Rows per page:")
        rpp_lbl.setObjectName("SubCaption")
        pag.addWidget(rpp_lbl)

        rpp = QComboBox()
        rpp.addItems(["10", "25", "50"])
        rpp.setFixedHeight(32)
        rpp.setFixedWidth(70)
        pag.addWidget(rpp)

        pag.addStretch()

        total = len(self._comments)
        self._pg_lbl = QLabel(f"1–{min(self._page_size, total)} of {total}")
        self._pg_lbl.setObjectName("SubCaption")
        pag.addWidget(self._pg_lbl)

        prev_btn = QPushButton("‹")
        prev_btn.setObjectName("SecondaryBtn")
        prev_btn.setFixedSize(32, 32)
        pag.addWidget(prev_btn)

        next_btn = QPushButton("›")
        next_btn.setObjectName("SecondaryBtn")
        next_btn.setFixedSize(32, 32)
        pag.addWidget(next_btn)

        root.addLayout(pag)

    # ── Data loading ──────────────────────────────────────────────

    def _load_comments(self) -> List[Any]:
        """Load comments from DB via controller, or fall back to mock data."""
        if self._controller and self._controller.current_drawing_id:
            db_comments = self._controller.get_comments_for_drawing(
                self._controller.current_drawing_id
            )
            if db_comments:
                return db_comments
        return list(md.COMMENTS)

    def reload_comments(self) -> None:
        """Reload table contents from the database. Call after new PDF is loaded."""
        self._comments = self._load_comments()
        self._model.removeRows(0, self._model.rowCount())
        for c in self._comments:
            self._append_row(c)

    # ── Model builder ─────────────────────────────────────────────

    def _build_model(self) -> QStandardItemModel:
        model = QStandardItemModel(0, 4)
        model.setHorizontalHeaderLabels(
            ["Comment ID", "OCR Text", "Confidence", "Status"]
        )
        for c in self._comments:
            self._append_row(c, model)
        return model

    def _append_row(
        self,
        c: Union[Dict[str, Any], Any],
        model: Optional[QStandardItemModel] = None,
    ) -> None:
        """Append a single comment row to the model."""
        if model is None:
            model = self._model

        cid        = _get(c, "id", "")
        ocr_text   = _get(c, "ocr_text", "")
        confidence = _get(c, "confidence", 0.0)
        status     = _get(c, "status", "Pending")

        id_item = QStandardItem(cid)
        id_item.setFont(QFont("Cascadia Code", 12))
        id_item.setEditable(False)

        text_item = QStandardItem(ocr_text)
        text_item.setEditable(True)   # Inline editing enabled

        conf_item = QStandardItem()
        conf_item.setData(float(confidence), Qt.ItemDataRole.UserRole)
        conf_item.setEditable(False)

        status_item = QStandardItem(status)
        status_item.setEditable(False)

        for item in [id_item, text_item, conf_item, status_item]:
            item.setTextAlignment(
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
            )
        model.appendRow([id_item, text_item, conf_item, status_item])

    # ── Persistence slot ──────────────────────────────────────────

    def _on_text_edited(self, top_left, bottom_right, roles) -> None:
        """
        Persist inline OCR text edits to the database.

        INTEGRATION NOTE:
        Only column 1 (OCR Text) is editable. When the edit role fires,
        we retrieve the comment ID from column 0 of the same row and call
        AppController.update_comment_text().

        Mock data IDs (format "C-NNNN") are skipped — they cannot be
        persisted because they are not in the database.
        """
        if Qt.ItemDataRole.EditRole not in roles:
            return
        if top_left.column() != 1:
            return

        row = top_left.row()
        id_item   = self._model.item(row, 0)
        text_item = self._model.item(row, 1)
        if id_item is None or text_item is None:
            return

        comment_id = id_item.text()
        new_text   = text_item.text()

        # Skip mock data — IDs in mock data use "C-NNNN" format
        if self._controller and comment_id and not comment_id.startswith("C-"):
            self._controller.update_comment_text(comment_id, new_text)
