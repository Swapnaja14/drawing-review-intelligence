import pytest
from src.services.classification_service import ClassificationService

def test_technical_comment_classified_correctly():
    service = ClassificationService()
    res = service.classify_comment("Incorrect member size: upgrade beam size W12x45 for span load")
    assert res.primary_category.category_name == "Technical"

def test_drafting_comment_classified():
    service = ClassificationService()
    res = service.classify_comment("Line overlap observed between dimension line and centerline")
    assert res.primary_category.category_name == "Drafting"

def test_dimension_comment_classified():
    service = ClassificationService()
    res = service.classify_comment("Incorrect dimension: overall length does not match elevation callout")
    assert res.primary_category.category_name == "Dimension"

def test_standards_comment_classified():
    service = ClassificationService()
    res = service.classify_comment("Codal issue: stair handrail height does not meet OSHA standard")
    assert res.primary_category.category_name == "Standards"

def test_coordination_comment_classified():
    service = ClassificationService()
    res = service.classify_comment("Clash with piping: 6 inch line conflicts with cable tray")
    assert res.primary_category.category_name == "Coordination"

def test_bom_comment_classified():
    service = ClassificationService()
    res = service.classify_comment("Incorrect part number in BOM: catalog number does not match vendor spec")
    assert res.primary_category.category_name == "BOM"

def test_low_confidence_flagged_for_review():
    service = ClassificationService()
    res = service.classify_comment("vague text")
    assert res.requires_human_review is True

def test_batch_classification_counts():
    service = ClassificationService()
    batch = [{"text": "Incorrect member size for beam"}, {"text": "vague text"}]
    res = service.classify_batch(batch)
    assert res.total_classified == 2

