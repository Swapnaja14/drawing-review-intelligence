from dataclasses import dataclass
from typing import Optional
from pathlib import Path

class ExportFormat:
    EXCEL = 'xlsx'
    JSON = 'json'
    CSV = 'csv'

@dataclass
class ExportConfigDTO:
    output_path: Path
    format: str = 'xlsx'
    include_summary_sheet: bool = True
    include_confidence_scores: bool = True
    filter_status: Optional[str] = None
    drawing_id: Optional[str] = None

@dataclass
class ExportResultDTO:
    output_path: Path
    format: str
    total_rows: int
    total_sheets: int
    file_size_bytes: int
    success: bool
    error_message: str = ''
