# Drawing Review Intelligence - API & Service Reference

Comprehensive API reference for core services, domain utilities, DTOs, and storage repositories.

---

## 1. Domain Utilities

### `src.core.domain.engineering_taxonomy`

- **`expand_engineering_abbreviations(text: str) -> Tuple[str, List[str]]`**:
  Expands ISO/ASME engineering abbreviations in `text` and returns the expanded text alongside a list of recognized terms.

- **`calculate_severity_score(priority_level: str, confidence: float, term_count: int) -> float`**:
  Calculates a composite severity score ($0.0$ to $1.0$) based on priority rating, AI confidence, and domain term density.

- **`resolve_discipline_from_filename(filename: str) -> Optional[DisciplineInfo]`**:
  Infers drawing discipline (Civil, Structural, Mechanical, Piping, Electrical, Instrumentation) from drawing filename or drawing number.

### `src.core.domain.drawing_rules.DrawingRuleEngine`

- **`calculate_sla_deadline(priority_level: str, created_at: Optional[datetime]) -> datetime`**:
  Calculates resolution SLA deadline target (HIGH: 24h, MEDIUM: 72h, LOW: 168h).

- **`evaluate_compliance(drawing_id: str, comments: List[Dict[str, Any]]) -> ComplianceReport`**:
  Evaluates drawing release readiness, unresolved high-priority comments, and overall compliance score.

---

## 2. Service Layer APIs

### `src.services.verification_service.VerificationService`

- **`approve_comment(comment_id: str, reviewer_id: str, notes: str = "") -> bool`**:
  Approves a pending comment and records an audit log entry.

- **`reject_comment(comment_id: str, reviewer_id: str, notes: str = "") -> bool`**:
  Rejects an invalid or duplicate comment.

- **`flag_comment(comment_id: str, reviewer_id: str, notes: str = "") -> bool`**:
  Flags a comment for lead engineer escalation.

### `src.services.analytics_service.AnalyticsService`

- **`get_global_kpis() -> KPISummaryDTO`**:
  Fetches global project, drawing, page, comment, and human verification accuracy counts.

- **`get_category_distribution(project_id: Optional[str] = None) -> List[CategoryDistributionDTO]`**:
  Returns comment breakdown grouped by classification category.

### `src.services.export_service.ExportService`

- **`export_drawing_comments(config: ExportConfigDTO) -> ExportResultDTO`**:
  Exports drawing comments to Excel (`.xlsx`), CSV (`.csv`), or JSON (`.json`) formats.

---

## 3. Utility Instrumentation APIs

### `src.utils.benchmark_utils`

- **`ExecutionTimer(name: str)`**: Context manager measuring code execution latency in milliseconds.
- **`calculate_latency_percentiles(durations_ms: List[float], op_name: str) -> MetricSummary`**: Calculates p50, p90, p99 percentiles and throughput.

### `src.utils.report_formatter`

- **`format_markdown_table(headers: List[str], rows: List[List[Any]]) -> str`**: Renders formatted Markdown tables.
- **`format_summary_card(title: str, metrics: Dict[str, Any]) -> str`**: Renders formatted ASCII summary cards.
