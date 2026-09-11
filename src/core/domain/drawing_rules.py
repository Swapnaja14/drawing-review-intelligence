"""
Drawing Compliance & SLA Rule Engine Module.

Provides rule-based compliance checking, reviewer workload tracking,
resolution SLA calculation, and drawing review readiness assessment.

Author: satyajeetvirkar22 <satyajeetvirkar22@gmail.com>
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta


@dataclass
class ReviewSLA:
    """Defines Service Level Agreement targets for comment resolution."""
    priority_level: str
    target_hours: int
    escalation_threshold_hours: int


SLA_DEFINITIONS: Dict[str, ReviewSLA] = {
    "HIGH": ReviewSLA("HIGH", target_hours=24, escalation_threshold_hours=12),
    "MEDIUM": ReviewSLA("MEDIUM", target_hours=72, escalation_threshold_hours=48),
    "LOW": ReviewSLA("LOW", target_hours=168, escalation_threshold_hours=120),
}


@dataclass
class ComplianceReport:
    """Summary report for drawing review compliance state."""
    drawing_id: str
    is_ready_for_release: bool
    total_comments: int
    pending_count: int
    approved_count: int
    rejected_count: int
    flagged_count: int
    unresolved_high_priority: int
    compliance_score: float
    violations: List[str] = field(default_factory=list)


class DrawingRuleEngine:
    """Rule engine for assessing drawing review compliance and SLA compliance."""

    def __init__(self, high_confidence_threshold: float = 0.85):
        self.high_confidence_threshold = high_confidence_threshold

    def calculate_sla_deadline(self, priority_level: str, created_at: Optional[datetime] = None) -> datetime:
        """Calculates the target resolution deadline based on priority SLA.
        
        Args:
            priority_level: HIGH, MEDIUM, or LOW.
            created_at: Datetime created or current datetime if None.
            
        Returns:
            Target resolution datetime.
        """
        start_time = created_at or datetime.now()
        sla = SLA_DEFINITIONS.get(priority_level.upper(), SLA_DEFINITIONS["LOW"])
        return start_time + timedelta(hours=sla.target_hours)

    def is_sla_breached(self, priority_level: str, created_at: datetime, resolved_at: Optional[datetime] = None) -> bool:
        """Checks if a comment resolution breached its priority SLA.
        
        Args:
            priority_level: Priority string.
            created_at: Creation timestamp.
            resolved_at: Resolution timestamp or current time if unresolved.
            
        Returns:
            True if SLA is breached, False otherwise.
        """
        end_time = resolved_at or datetime.now()
        deadline = self.calculate_sla_deadline(priority_level, created_at)
        return end_time > deadline

    def evaluate_compliance(self, drawing_id: str, comments: List[Dict[str, Any]]) -> ComplianceReport:
        """Evaluates drawing readiness and compliance score across all extracted comments.
        
        Args:
            drawing_id: Identifier of the drawing.
            comments: List of comment dictionaries.
            
        Returns:
            ComplianceReport dataclass.
        """
        if not comments:
            return ComplianceReport(
                drawing_id=drawing_id,
                is_ready_for_release=True,
                total_comments=0,
                pending_count=0,
                approved_count=0,
                rejected_count=0,
                flagged_count=0,
                unresolved_high_priority=0,
                compliance_score=1.0,
                violations=[],
            )

        total = len(comments)
        pending = sum(1 for c in comments if c.get("status", "").lower() == "pending")
        approved = sum(1 for c in comments if c.get("status", "").lower() == "approved")
        rejected = sum(1 for c in comments if c.get("status", "").lower() == "rejected")
        flagged = sum(1 for c in comments if c.get("status", "").lower() == "flagged")

        unresolved_high = sum(
            1 for c in comments
            if c.get("priority_level", "").upper() == "HIGH" and c.get("status", "").lower() in ("pending", "flagged")
        )

        violations = []
        if pending > 0:
            violations.append(f"Drawing has {pending} unresolved pending comment(s).")
        if unresolved_high > 0:
            violations.append(f"Drawing has {unresolved_high} unresolved HIGH priority comment(s).")
        if flagged > 0:
            violations.append(f"Drawing has {flagged} flagged comment(s) requiring escalation.")

        # Compliance score: resolved ratio penalized by unresolved high priority
        resolved = approved + rejected
        base_ratio = resolved / total
        penalty = (unresolved_high / total) * 0.5
        score = max(0.0, round(base_ratio - penalty, 4))

        is_ready = (pending == 0) and (unresolved_high == 0) and (flagged == 0)

        return ComplianceReport(
            drawing_id=drawing_id,
            is_ready_for_release=is_ready,
            total_comments=total,
            pending_count=pending,
            approved_count=approved,
            rejected_count=rejected,
            flagged_count=flagged,
            unresolved_high_priority=unresolved_high,
            compliance_score=score,
            violations=violations,
        )
