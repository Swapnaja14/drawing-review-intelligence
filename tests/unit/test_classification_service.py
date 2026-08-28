import pytest
from src.services.classification_service import ClassificationService

def test_piping_comment_classified_correctly():
    service = ClassificationService()
    res = service.classify_comment("Check valve flange alignment")
    assert res.primary_category.category_name == "Piping/Process"

def test_electrical_comment_classified():
    service = ClassificationService()
    res = service.classify_comment("Cable tray routing near panel")
    assert res.primary_category.category_name == "Electrical/Instrumentation"

def test_structural_comment_classified():
    service = ClassificationService()
    res = service.classify_comment("Foundation bolt anchor plate")
    assert res.primary_category.category_name == "Structural/Civil"

def test_safety_comment_classified():
    service = ClassificationService()
    res = service.classify_comment("Emergency shutdown valve missing")
    assert res.primary_category.category_name == "Safety/HSE"

def test_dimensional_comment_classified():
    service = ClassificationService()
    res = service.classify_comment("Tolerance on diameter exceeds limit")
    assert res.primary_category.category_name == "Dimensional/Tolerancing"

def test_low_confidence_flagged_for_review():
    service = ClassificationService()
    res = service.classify_comment("vague text")
    assert res.requires_human_review is True

def test_batch_classification_counts():
    service = ClassificationService()
    batch = [{"text": "Check valve"}, {"text": "vague text"}]
    res = service.classify_batch(batch)
    assert res.total_classified == 2
