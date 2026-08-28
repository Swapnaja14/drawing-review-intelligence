import pytest
import json
import csv
from pathlib import Path
from src.core.dtos.export_dtos import ExportConfigDTO, ExportFormat
from src.services.export_service import ExportService, OPENPYXL_AVAILABLE

class MockCommentRepo:
    def get_comments_for_drawing(self, drawing_id):
        return [
            {'id': '1', 'drawing_id': drawing_id, 'status': 'Pending', 'raw_text': 'test1', 'confidence': 0.9},
            {'id': '2', 'drawing_id': drawing_id, 'status': 'Approved', 'raw_text': 'test2', 'confidence': 0.95},
        ]

class MockProjectRepo:
    pass

def test_export_to_json_creates_file(tmp_path):
    repo = MockCommentRepo()
    service = ExportService(repo, MockProjectRepo())
    out_file = tmp_path / "out.json"
    
    config = ExportConfigDTO(output_path=out_file, format=ExportFormat.JSON, drawing_id="draw1")
    res = service.export_drawing_comments(config)
    
    assert res.success is True
    assert res.total_rows == 2
    assert out_file.exists()
    
    with open(out_file) as f:
        data = json.load(f)
        assert data['metadata']['total_records'] == 2
        assert len(data['comments']) == 2

def test_export_to_csv_creates_file(tmp_path):
    repo = MockCommentRepo()
    service = ExportService(repo, MockProjectRepo())
    out_file = tmp_path / "out.csv"
    
    config = ExportConfigDTO(output_path=out_file, format=ExportFormat.CSV, drawing_id="draw1")
    res = service.export_drawing_comments(config)
    
    assert res.success is True
    assert res.total_rows == 2
    assert out_file.exists()
    
    with open(out_file, newline='') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        assert len(rows) == 2

def test_export_result_dto_fields(tmp_path):
    repo = MockCommentRepo()
    service = ExportService(repo, MockProjectRepo())
    out_file = tmp_path / "out.json"
    
    config = ExportConfigDTO(output_path=out_file, format=ExportFormat.JSON, drawing_id="draw1")
    res = service.export_drawing_comments(config)
    
    assert hasattr(res, 'output_path')
    assert hasattr(res, 'format')
    assert hasattr(res, 'total_rows')
    assert hasattr(res, 'total_sheets')
    assert hasattr(res, 'file_size_bytes')
    assert hasattr(res, 'success')
    assert hasattr(res, 'error_message')

def test_export_config_defaults():
    config = ExportConfigDTO(output_path=Path("test.xlsx"))
    assert config.format == 'xlsx'
    assert config.include_summary_sheet is True
    assert config.include_confidence_scores is True
    assert config.filter_status is None
    assert config.drawing_id is None

@pytest.mark.skipif(not OPENPYXL_AVAILABLE, reason="openpyxl not installed")
def test_excel_export_if_openpyxl_available(tmp_path):
    repo = MockCommentRepo()
    service = ExportService(repo, MockProjectRepo())
    out_file = tmp_path / "out.xlsx"
    
    config = ExportConfigDTO(output_path=out_file, format=ExportFormat.EXCEL, drawing_id="draw1")
    res = service.export_drawing_comments(config)
    
    assert res.success is True
    assert out_file.exists()
    assert res.file_size_bytes > 0
