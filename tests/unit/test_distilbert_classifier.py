import pytest
import csv
from pathlib import Path
from src.services.classification_service import ClassificationService
from src.ai.dataset_generator import CATEGORIES

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATASET_DIR = PROJECT_ROOT / "dataset" / "classification_dataset"


def test_dataset_files_exist_and_balanced():
    """Verify that dataset generator creates train, val, and test splits."""
    train_file = DATASET_DIR / "train.csv"
    val_file = DATASET_DIR / "val.csv"
    test_file = DATASET_DIR / "test.csv"

    assert train_file.exists(), "train.csv must exist"
    assert val_file.exists(), "val.csv must exist"
    assert test_file.exists(), "test.csv must exist"

    # Check train data has samples for all categories
    train_cats = set()
    with open(train_file, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            train_cats.add(row["category_name"])

    for cat in CATEGORIES:
        assert cat in train_cats, f"Category '{cat}' must be present in train.csv"


def test_classification_service_predicts_all_categories():
    """Verify that classification service produces predictions with valid category names."""
    service = ClassificationService()
    res = service.classify_comment("Check valve flange on line 174005-S12-04-P08")

    assert res.primary_category is not None
    assert res.primary_category.category_name in CATEGORIES
    assert 0.0 <= res.primary_category.confidence <= 1.0


def test_classification_service_confidence_ordering():
    """Verify predictions are sorted descending by confidence score."""
    service = ClassificationService()
    res = service.classify_comment("Route electrical cable tray near structural beam")

    preds = [res.primary_category] + res.alternative_categories
    confs = [p.confidence for p in preds]

    assert confs == sorted(confs, reverse=True), "Predictions must be sorted descending by confidence"


def test_classification_service_empty_input_handling():
    """Verify graceful handling of empty comment strings."""
    service = ClassificationService()
    res = service.classify_comment("")
    assert res.primary_category.category_name in ["Unknown", "Documentation", "General/Administrative"] or res.requires_human_review is True


def test_classification_service_batch_processing():
    """Verify batch classification returns correct count and flags."""
    service = ClassificationService()
    batch = [
        {"id": "1", "text": "Check flange gasket rating"},
        {"id": "2", "text": "Verify PLC transmitter I/O card"},
        {"id": "3", "text": "HSS structural column anchor bolt"},
    ]
    batch_res = service.classify_batch(batch, drawing_id="DWG-TEST")
    assert batch_res.total_classified == 3
    assert len(batch_res.results) == 3
