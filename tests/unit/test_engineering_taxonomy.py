"""
Unit tests for src/core/domain/engineering_taxonomy.py

Author: satyajeetvirkar22 <satyajeetvirkar22@gmail.com>
"""

import pytest
from src.core.domain.engineering_taxonomy import (
    DISCIPLINE_CATALOG,
    ENGINEERING_ABBREVIATIONS,
    ACTION_VERBS,
    expand_engineering_abbreviations,
    calculate_severity_score,
    resolve_discipline_from_filename,
)


def test_discipline_catalog_structure():
    assert "CIV" in DISCIPLINE_CATALOG
    assert "STR" in DISCIPLINE_CATALOG
    assert "MEC" in DISCIPLINE_CATALOG
    assert "ELE" in DISCIPLINE_CATALOG
    assert "PIP" in DISCIPLINE_CATALOG
    assert "INS" in DISCIPLINE_CATALOG
    
    str_info = DISCIPLINE_CATALOG["STR"]
    assert str_info.code == "STR"
    assert "structural" in str_info.keywords


def test_engineering_abbreviation_count():
    assert len(ENGINEERING_ABBREVIATIONS) >= 100
    assert ENGINEERING_ABBREVIATIONS["P&ID"] == "Piping and Instrumentation Diagram"
    assert ENGINEERING_ABBREVIATIONS["BOM"] == "Bill of Materials"
    assert ENGINEERING_ABBREVIATIONS["HSS"] == "Hollow Structural Section"


def test_expand_engineering_abbreviations():
    text = "PLEASE VERIFY P&ID AND CHECK HSS WELDING IN BOM"
    res_text, terms = expand_engineering_abbreviations(text)
    assert "P&ID" in terms
    assert "HSS" in terms
    assert "BOM" in terms


def test_calculate_severity_score():
    high_score = calculate_severity_score("HIGH", 0.95, 3)
    low_score = calculate_severity_score("LOW", 0.50, 0)
    
    assert 0.0 <= high_score <= 1.0
    assert 0.0 <= low_score <= 1.0
    assert high_score > low_score


def test_resolve_discipline_from_filename():
    d_civ = resolve_discipline_from_filename("C-101-SITE-GRADING.pdf")
    d_str = resolve_discipline_from_filename("S-201-FOUNDATION-PLAN.pdf")
    d_pip = resolve_discipline_from_filename("P-301-ISOMETRIC-SPOOL.pdf")
    
    assert d_civ is not None and d_civ.code == "CIV"
    assert d_str is not None and d_str.code == "STR"
    assert d_pip is not None and d_pip.code == "PIP"
