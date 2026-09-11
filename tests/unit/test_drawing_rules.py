"""
Unit tests for src/core/domain/drawing_rules.py

Author: satyajeetvirkar22 <satyajeetvirkar22@gmail.com>
"""

import pytest
from datetime import datetime, timedelta
from src.core.domain.drawing_rules import DrawingRuleEngine, ComplianceReport


def test_calculate_sla_deadline():
    engine = DrawingRuleEngine()
    now = datetime(2026, 1, 1, 12, 0, 0)
    
    high_deadline = engine.calculate_sla_deadline("HIGH", now)
    med_deadline = engine.calculate_sla_deadline("MEDIUM", now)
    low_deadline = engine.calculate_sla_deadline("LOW", now)
    
    assert high_deadline == now + timedelta(hours=24)
    assert med_deadline == now + timedelta(hours=72)
    assert low_deadline == now + timedelta(hours=168)


def test_is_sla_breached():
    engine = DrawingRuleEngine()
    created = datetime(2026, 1, 1, 12, 0, 0)
    
    # 10 hours later: not breached for HIGH (24h)
    assert not engine.is_sla_breached("HIGH", created, created + timedelta(hours=10))
    # 30 hours later: breached for HIGH (24h)
    assert engine.is_sla_breached("HIGH", created, created + timedelta(hours=30))


def test_evaluate_compliance_empty():
    engine = DrawingRuleEngine()
    report = engine.evaluate_compliance("DWG-001", [])
    
    assert report.is_ready_for_release is True
    assert report.compliance_score == 1.0
    assert len(report.violations) == 0


def test_evaluate_compliance_with_unresolved_high():
    engine = DrawingRuleEngine()
    comments = [
        {"id": "1", "status": "Approved", "priority_level": "LOW"},
        {"id": "2", "status": "Pending", "priority_level": "HIGH"},
        {"id": "3", "status": "Approved", "priority_level": "MEDIUM"},
    ]
    
    report = engine.evaluate_compliance("DWG-002", comments)
    
    assert report.is_ready_for_release is False
    assert report.unresolved_high_priority == 1
    assert report.pending_count == 1
    assert report.approved_count == 2
    assert len(report.violations) > 0
