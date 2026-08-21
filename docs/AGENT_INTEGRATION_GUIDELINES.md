# Agent Integration Guidelines
# UCC AI Drawing Review Intelligence
# ============================================================
# This document is for ALL development agents working on this project.
# It describes the agreed architecture, data contracts, and known
# integration warnings discovered during code inspection.
#
# DO NOT:
#   - Mention individual names
#   - Assign blame
#   - Silently rewrite another responsibility's work
#
# DO:
#   - Follow the common architecture
#   - Document new conflicts in this file
#   - Add ARCHITECTURE WARNING comments in source files where appropriate
# ============================================================

---

## 1. Project Architecture

All features must follow this layered flow:

```
UI Screens (PySide6)
        ↓
  AppController
        ↓
  Application Services  (PDFService, future OCR/AI service)
        ↓
  Repositories          (DrawingRepository, CommentRepository, etc.)
        ↓
  SQLAlchemy ORM
        ↓
  SQLite (local dev)
```

Additional infrastructure adapters sit alongside repositories:

```
PyMuPDF Adapter  ← implements IPDFLoader
OCR/AI Adapter   ← implements future IOCRLoader / IClassifier
```

---

## 2. Architecture Rules

### 2.1 Layer Boundaries

- **UI screens must NOT** directly import or use SQLAlchemy, SQLite, PyMuPDF (`fitz`),
  OCR libraries, or AI inference libraries.
- **Repositories must NOT** contain UI logic, Qt signals, or widget references.
- **Business logic** (validation, status transitions, human-verification rules) belongs
  in the controller or a dedicated service — not inside UI widget methods.
- **Do not create duplicate data models** for the same entity. One source of truth per
  entity: `CommentModel`, `DrawingModel`, `ProjectModel`, etc.
- **Do not maintain multiple sources of truth** for the same application state.
  Example: a screen should not hold its own in-memory copy of comment statuses that
  diverges from the database.

### 2.2 Technology Consistency

Current approved stack:
- Python 3.12
- PySide6 >= 6.7 for desktop UI
- SQLAlchemy >= 2.0 for ORM
- SQLite for local/single-machine development
- PyMuPDF >= 1.23 for PDF processing
- qtawesome >= 1.3 for icons
- pytest >= 7.4 for testing

**Do not introduce** a second ORM, a second PDF library, a second UI framework,
or a competing database engine without explicit team agreement and documented
justification.

Before adding any new dependency:
1. Check whether an existing dependency already solves the problem.
2. Verify Python and PySide6 compatibility.
3. Confirm the package is actively maintained.
4. Assess future deployment implications.

### 2.3 SQLite / Database Rules

- SQLite is the **local development database only**.
- It is acceptable for single-machine, single-user operation.
- If multiple simultaneous users need to share data, SQLite is not appropriate.
  The repository layer is designed to be database-agnostic via SQLAlchemy so
  migration to PostgreSQL is possible without changing repository interfaces.
- **Do NOT commit** the SQLite database file (`data/ucc_database.db`) to Git.
  Only models, repositories, initialisation scripts, and verification scripts
  are version-controlled.
- Do not use SQLite-specific SQL syntax in repository methods (other than the
  `PRAGMA` statements already in `DatabaseEngine`). This preserves PostgreSQL
  migration compatibility.

### 2.4 Data Contracts

Do not allow different screens or features to invent their own field names for
the same concept. The agreed field names for a comment are:

| Concept      | DB column       | Controller/display dict key | Mock field (legacy) |
|--------------|-----------------|----------------------------|---------------------|
| Comment ID   | `id`            | `"id"`                     | `c.id`              |
| Drawing FK   | `drawing_id`    | `"drawing_id"`             | (no equivalent)     |
| Page number  | `page_number`   | `"page"`                   | `c.page`            |
| OCR text     | `raw_text`      | `"ocr_text"`               | `c.ocr_text`        |
| Category     | `category_name` | `"category"`               | `c.category`        |
| Confidence   | `confidence`    | `"confidence"`             | `c.confidence`      |
| Status       | `status`        | `"status"`                 | `c.status`          |
| Reviewer     | `user_id` (FK)  | `"reviewer"`               | `c.reviewer`        |
| Timestamp    | `created_at`    | `"timestamp"`              | `c.timestamp`       |
| Drawing ref  | (via JOIN)      | `"drawing_no"`             | `c.drawing_no`      |

Conversion between DB dicts and display dicts is performed by
`AppController.normalise_comment()`. Do not scatter field-name translations
throughout UI files.

### 2.5 Bounding Box Coordinate System

**This is the most critical data contract in the project.**

```
DATABASE format (CommentModel):
    bbox_x0, bbox_y0, bbox_x1, bbox_y1
    — absolute PDF point coordinates (1 pt = 1/72 inch)
    — origin: top-left of page
    — x0=left, y0=top, x1=right, y1=bottom

MOCK DATA format (mock_data.Comment.bbox):
    (x, y, width, height)
    — normalised 0.0–1.0 relative to page dimensions

PyMuPDF output (extract_page_text_blocks):
    (x0, y0, x1, y1)
    — absolute PDF point coordinates  ← matches database format
```

**Do NOT** apply mock bbox values to database bbox storage or vice versa.

Conversion formula (absolute points → normalised, for canvas rendering):
```python
x_norm = bbox_x0 / page_width_pt
y_norm = bbox_y0 / page_height_pt
w_norm = (bbox_x1 - bbox_x0) / page_width_pt
h_norm = (bbox_y1 - bbox_y0) / page_height_pt
```

Page dimensions in points are available from:
- `PageMetadataDTO.width_pt` / `height_pt`  (in memory after PDF load)
- `PageModel.width_pt` / `height_pt`        (in database)

### 2.6 Comment Status Vocabulary

Permitted values (exactly as written — case-sensitive):

```
"Pending"   — default for new comments
"Approved"  — human reviewer approved
"Rejected"  — human reviewer rejected
"Flagged"   — flagged for further review
```

Do not introduce `"done"`, `"accepted"`, `"reviewed"`, or any other value.
All UI components (`StatusChip`, `StatusDelegate`) and the `CommentModel` are
calibrated to exactly these four strings.

### 2.7 Drawing ID Mapping

```
PDF filename  ≠  DrawingModel.id
```

`DrawingModel.id` is a UUID-based string generated by `DrawingRepository`
at save time: `"DWG-{uuid4().hex[:8].upper()}"`.

`PDFDocumentDTO.file_name` is the bare filename (e.g. `"UCC-E-101.pdf"`).

`AppController.current_drawing_id` is the authoritative in-session drawing ID.
Always use this property when associating comments with the loaded drawing.

### 2.8 Threading

- PDF processing, OCR inference, AI classification, and potentially large DB
  write operations must NOT block the PySide6 UI (main) thread.
- The existing `QThread`-based worker pattern (`PDFLoadWorker`, `PDFRenderWorker`)
  is the approved mechanism. Reuse it; do not create a competing threading
  architecture.
- Small SQLite reads/writes (comment status updates, single-row fetches) are
  currently performed synchronously on the UI thread. This is acceptable for
  local SQLite. If response time becomes a problem, move these to workers using
  the existing pattern.

---

## 3. Integration Warnings

The following issues were discovered during code inspection. They are documented
here so every agent is aware before extending the affected features.

---

### WARNING-001

**FEATURE / FILE:** `app/components/pdf_canvas.py` — `make_page_pixmap()` function

**PROBLEM:**
`pdf_canvas.py` imports `mock_data` at module level and hardcodes
`md.COMMENTS[:5]` inside `make_page_pixmap()`. This renders five mock
bounding boxes on every simulated drawing page, regardless of which drawing
is loaded or whether any database comments exist.

**WHY IT MATTERS:**
`make_page_pixmap()` is used as the canvas background by `review_screen.py`,
`comment_viewer_screen.py`, and `pdf_viewer_screen.py`. When these screens
are connected to database comments, the canvas will render mock bounding
boxes while the comment list shows real database records — creating a split
data source on the same screen.

**CONFLICTING RESPONSIBILITY:** Database integration / Comment Viewer rendering

**POSSIBLE FUTURE PROBLEM:**
After database integration, the canvas and the comment list will show
different data. Bounding box positions will be incorrect because mock bbox
uses normalised `(x, y, w, h)` while database bbox uses absolute PDF points.

**RECOMMENDED DIRECTION:**
`make_page_pixmap()` should accept an optional `comments` parameter.
The calling screen passes real or empty comment data. The mock fallback
remains for screens not yet connected to the controller.

---

### WARNING-002

**FEATURE / FILE:** `app/components/charts.py` — `build_pareto_chart()`, `build_monthly_chart()`, `build_category_pie()`

**PROBLEM:**
All three chart builder functions import `mock_data` at module level and
fetch `md.PARETO_DATA`, `md.MONTHLY_COUNTS`, `md.CATEGORY_COUNTS` directly
inside the function body. Chart components should not fetch their own data.

**WHY IT MATTERS:**
When `analytics_screen.py` is wired to database aggregation queries, there
will be two competing data sources: the database result (from `AppController`)
and the hardcoded mock data (from `charts.py`). The charts will not update
unless `charts.py` is also modified, which is not obvious from the screen code.

**CONFLICTING RESPONSIBILITY:** Analytics screen / Database aggregation

**POSSIBLE FUTURE PROBLEM:**
Phase 8 analytics integration must modify both `analytics_screen.py` AND
`charts.py`. An agent modifying only the screen will see no visual change.

**RECOMMENDED DIRECTION:**
Refactor chart builder functions to accept data as parameters:
`build_pareto_chart(categories, counts, cumulative)`.
`analytics_screen.py` fetches data from the controller and passes it in.

---

### WARNING-003

**FEATURE / FILE:** `app/screens/dashboard_screen.py` — `DashboardPage._build_projects_table()`

**PROBLEM:**
When `p` is a dict (live database result), the code accesses `p["drawings"]`
and `p["comments"]`. These keys do not exist in `_project_to_dict()` output
from `ProjectRepository`. `ProjectModel` has no `drawings_count` or
`comments_count` column.

**WHY IT MATTERS:**
This will raise `KeyError` when `get_all_projects()` returns real database
data, silently breaking the projects table on the dashboard.

**CONFLICTING RESPONSIBILITY:** Dashboard UI / ProjectRepository output contract

**POSSIBLE FUTURE PROBLEM:**
Dashboard silently shows empty or crashes when database has real project data.

**RECOMMENDED DIRECTION:**
Either add subquery aggregation to `ProjectRepository.get_all_projects()`
(counting drawings and comments per project), or handle missing keys with
`p.get("drawings", "—")` as a safe temporary measure.

---

### WARNING-004

**FEATURE / FILE:** `app/screens/classification_screen.py` — `ClassificationPage._open_drawer()`

**PROBLEM:**
`_open_drawer()` uses `md.COMMENTS[row]` as a direct list index after proxy
model row mapping. The table uses `QSortFilterProxyModel` for text search.
When a search filter is active, the source-model row index does not correspond
to the raw mock list index.

**WHY IT MATTERS:**
With an active filter, the wrong comment is shown in the inspector drawer.
This is a correctness bug in the current mock implementation that will become
a data integrity issue when the table is loaded from database records.

**CONFLICTING RESPONSIBILITY:** Classification screen / Comment data source

**POSSIBLE FUTURE PROBLEM:**
When classification screen is connected to database, `md.COMMENTS[row]` will
either reference the wrong comment or raise `IndexError` if the database has
a different number of comments than the mock list.

**RECOMMENDED DIRECTION:**
The model already stores `c.id` in `Qt.ItemDataRole.UserRole` on `text_item`.
`_open_drawer()` should retrieve the comment ID from `UserRole`, then look up
the comment from the instance comment list by ID — not by raw row index.

---

### WARNING-005

**FEATURE / FILE:** `app/screens/review_screen.py` — `HumanReviewPage._toggle_edit()`

**PROBLEM:**
The "Save" button action (`_toggle_edit`) only changes the button label and
toggles the text field's read-only state. No persistence call is made.
Edited OCR text is lost when the screen is navigated away from or the app
is closed.

**WHY IT MATTERS:**
Users can edit OCR text in the review screen but changes are never saved.
This creates an expectation mismatch: the UI implies saving but does not persist.

**CONFLICTING RESPONSIBILITY:** Review screen / Comment persistence (database responsibility)

**POSSIBLE FUTURE PROBLEM:**
When the controller is connected, the save action must call
`controller.update_comment_text(comment_id, new_text)`. Without this,
OCR corrections made in the review screen will always be lost.

**RECOMMENDED DIRECTION:**
When toggling from edit mode back to read-only (`ro` is `True` before toggle),
call `controller.update_comment_text(comment_id, self._ocr_edit.toPlainText())`.

---

### WARNING-006

**FEATURE / FILE:** `app/controllers/app_controller.py` — `PDFLoadWorker.run()`

**PROBLEM:**
`save_drawing_from_dto()` returns `{"id": "DWG-XXXXXXXX", ...}` but the
return value is not captured. The database-generated `drawing_id` is
discarded immediately after the drawing is saved.

**WHY IT MATTERS:**
`CommentModel.drawing_id` is a foreign key referencing `DrawingModel.id`.
Without capturing `drawing_id`, no comment can be correctly associated with
the loaded drawing. `controller.current_document.file_name` is NOT the drawing
ID and must not be used as a substitute.

**CONFLICTING RESPONSIBILITY:** Drawing ID propagation / Comment persistence

**POSSIBLE FUTURE PROBLEM:**
Every comment-related feature (review, OCR results, classification, comment
viewer) requires the `drawing_id`. Without it, all comment queries will
return no results or store orphaned records.

**RECOMMENDED DIRECTION:**
Capture `result = self.drawing_repo.save_drawing_from_dto(doc_dto)` and pass
`result["id"]` up to `AppController` via the success signal. Store it as
`self._current_drawing_id` and expose via `current_drawing_id` property.

---

### WARNING-007

**FEATURE / FILE:** `app/controllers/app_controller.py` — `AppController.__init__()`

**PROBLEM:**
`CommentRepository` is defined in `repository.py` but is never instantiated
in `AppController`. No comment-related operation is accessible from any screen.

**WHY IT MATTERS:**
All four comment-dependent screens (`review_screen`, `ocr_results_screen`,
`classification_screen`, `comment_viewer_screen`) have no path to comment
persistence or retrieval. The entire comment database integration is blocked.

**CONFLICTING RESPONSIBILITY:** AppController / Comment database responsibility

**RECOMMENDED DIRECTION:**
Add `self.comment_repo = CommentRepository(self.db_engine)` to `__init__`.
Expose proxy methods: `get_comments_for_drawing`, `update_comment_status`,
`update_comment_text`, `get_category_counts`, `normalise_comment`.

---

### WARNING-008

**FEATURE / FILE:** `app/main_window.py` — `MainWindow.__init__()` `_pages` list

**PROBLEM:**
`CommentHighlightPage()`, `OcrResultsPage()`, `ClassificationPage()`, and
`HumanReviewPage()` are instantiated without `controller=self.controller`.
These four screens have no `controller` parameter in their `__init__` signature.

**WHY IT MATTERS:**
Without a controller reference, these screens cannot call any database
operation. They are permanently locked to mock data regardless of what is
implemented in the controller and repositories.

**CONFLICTING RESPONSIBILITY:** Main window wiring / Database integration for comment screens

**RECOMMENDED DIRECTION:**
Add `controller=None` parameter to all four screen constructors. Pass
`controller=self.controller` in `MainWindow._pages` list for each screen.

---

### WARNING-009

**FEATURE / FILE:** `src/infrastructure/storage/repository.py` — `CommentRepository.save_comment()` bbox parameter

**PROBLEM:**
The `bbox` parameter is typed as `tuple[float, float, float, float]` with no
documentation of the expected coordinate system. The method stores values as
`bbox_x0=bbox[0], bbox_y0=bbox[1], bbox_x1=bbox[2], bbox_y1=bbox[3]` —
expecting absolute PDF point coordinates `(x0, y0, x1, y1)`.

**WHY IT MATTERS:**
Any caller that passes normalised `(x, y, w, h)` coordinates will silently
store incorrect bounding box data. Bounding boxes will render at wrong
positions in the comment viewer.

**CONFLICTING RESPONSIBILITY:** OCR/AI pipeline → Database storage → Comment Viewer rendering

**RECOMMENDED DIRECTION:**
Add a docstring to `save_comment()` explicitly stating:
`bbox: (x0, y0, x1, y1) in absolute PDF point coordinates.
Do NOT pass normalised or (x, y, w, h) format coordinates.`

---

### WARNING-010

**FEATURE / FILE:** All comment-dependent screens — field name mismatch between mock objects and DB dicts

**PROBLEM:**
Mock `Comment` dataclass uses attribute names: `.ocr_text`, `.page`,
`.category`, `.drawing_no`, `.reviewer`, `.timestamp`.
`_comment_to_dict()` returns keys: `"raw_text"`, `"page_number"`,
`"category_name"`, (no `drawing_no`), `"user_id"`, `"created_at"`.

**WHY IT MATTERS:**
Any screen that switches from mock objects to DB dicts without a mapping
layer will silently read `None` for every field or raise `AttributeError`.

**CONFLICTING RESPONSIBILITY:** All comment UI screens / Repository output contract

**POSSIBLE FUTURE PROBLEM:**
Silent data loss, empty tables, incorrect category filters, missing drawing
numbers in review panel — without any exception being raised.

**RECOMMENDED DIRECTION:**
A single `normalise_comment(db_dict)` function in `AppController` maps DB
dict keys to the display dict shape used by all screens. All screens consume
only the normalised format. Conversion happens once, at the controller boundary.

---

## 4. Mock Data Migration Status

| Data | Current source | Target source | Status |
|------|---------------|---------------|--------|
| `COMMENTS` | `mock_data.py` | `CommentRepository` | In progress — Week 3 |
| `CATEGORY_COUNTS` | `mock_data.py` | `CommentRepository.get_category_counts()` | In progress — Week 3 |
| `PROJECTS` | `mock_data.py` | `ProjectRepository.get_all_projects()` | Partially done (dashboard) |
| `KPI` totals | `mock_data.py` | `ProjectRepository.get_kpis()` | Partially done (dashboard) |
| `MONTHLY_COUNTS` | `mock_data.py` | SQL GROUP BY on `comments.created_at` | Phase 8 |
| `PARETO_DATA` | `mock_data.py` | SQL GROUP BY on `comments.category_name` | Phase 8 |
| `ACTIVITIES` | `mock_data.py` | Future `ActivityLog` table or derived query | Deferred |
| `JOBS` | `mock_data.py` | Future processing status mechanism | Deferred |
| `EXPORT_HISTORY` | `mock_data.py` | Future `ExportRecord` table | Deferred |

`mock_data.py` must NOT be deleted until all dependent screens have been
verified against live database data.

---

## 5. File Ownership / Responsibility Map

| File | Responsibility | Notes |
|------|---------------|-------|
| `src/core/dtos/pdf_dtos.py` | PDF processing | Do not add DB-layer fields |
| `src/core/interfaces/pdf_loader.py` | PDF processing | Interface — do not modify |
| `src/core/exceptions/pdf_exceptions.py` | PDF processing | Do not modify |
| `src/infrastructure/pdf/pymupdf_adapter.py` | PDF processing | Only place `fitz` is imported |
| `src/services/pdf_service.py` | PDF service | Do not add DB logic here |
| `src/infrastructure/storage/models.py` | Database schema | Schema changes require review of all callers |
| `src/infrastructure/storage/repository.py` | Database access | All DB access must go through here |
| `src/infrastructure/logging/logger.py` | Shared infrastructure | Do not modify |
| `app/controllers/app_controller.py` | Controller / wiring | Owns current_document, current_drawing_id |
| `app/main_window.py` | Application shell | Owns page wiring and controller instantiation |
| `app/mock_data.py` | Development fallback | Keep until DB integration verified |
| `app/theme.py` | UI theming | Do not modify for DB work |
| `app/screens/upload_screen.py` | Upload UI | Already DB-connected |
| `app/screens/pdf_viewer_screen.py` | PDF Viewer UI | Already DB-connected |
| `app/screens/dashboard_screen.py` | Dashboard UI | Partially DB-connected |
| `app/screens/splash_screen.py` | Startup UI | No data dependency |
| `app/screens/home_screen.py` | Landing UI | No data dependency |
| `app/screens/export_screen.py` | Export UI | Deferred |
| `app/screens/settings_screen.py` | Settings UI | Deferred |
| `app/components/*` | Reusable UI components | Pure presentation — no DB/service imports |
| `scripts/verify_db.py` | DB verification | Do not modify |
| `data/ucc_database.db` | Runtime artifact | Never commit to Git |

---

## 6. Approved Week 3 Implementation Order

1. Add `update_comment_status`, `update_comment_text`, `get_category_counts`
   to `CommentRepository` in `repository.py`
2. Fix `PDFLoadWorker.run()` to capture `drawing_id` from `save_drawing_from_dto`
3. Add `_current_drawing_id` + `current_drawing_id` property to `AppController`
4. Instantiate `CommentRepository` in `AppController.__init__`
5. Add `normalise_comment()` + 4 proxy methods to `AppController`
6. Add `controller` parameter to `HumanReviewPage`, `OcrResultsPage`,
   `ClassificationPage`, `CommentHighlightPage`
7. Integrate review screen (load, approve, reject, edit-save)
8. Integrate OCR results screen (load, text edit persistence)
9. Integrate classification screen (load comments + category counts)
10. Integrate comment viewer screen (load comments + bbox conversion)
11. Update `MainWindow` to pass controller to all four screens
12. Fix `pdf_canvas.py` `make_page_pixmap()` to accept optional comments param
13. Phase 8 (deferred): analytics aggregation + parameterise `charts.py`
