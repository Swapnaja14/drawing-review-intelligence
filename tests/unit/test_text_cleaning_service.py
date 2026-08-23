import pytest
from src.services.text_cleaning_service import TextCleaningService

def test_remove_ocr_noise():
    service = TextCleaningService()
    res = service.clean_text("Hello!!!")
    assert res.cleaned_text == "Hello!"

def test_normalize_whitespace():
    service = TextCleaningService()
    res = service.clean_text("Too   much    space")
    assert res.cleaned_text == "Too much space"

def test_engineering_abbreviation_expansion():
    service = TextCleaningService()
    res = service.clean_text("Check P&ID")
    assert "Piping and Instrumentation Diagram" in res.cleaned_text

def test_duplicate_detection():
    service = TextCleaningService()
    dups = service.detect_duplicates(["same text", "same text"])
    assert len(dups) == 1

def test_clean_batch_returns_stats():
    service = TextCleaningService()
    batch = [{"text": "A"}, {"text": "B"}, {"text": "C"}, {"text": "D"}, {"text": "E"}]
    res = service.clean_batch(batch)
    assert res.total_comments == 5

def test_similarity_score_range():
    service = TextCleaningService()
    res = service.clean_text("Text")
    assert 0.0 <= res.similarity_score <= 1.0
