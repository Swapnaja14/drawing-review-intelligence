from dataclasses import dataclass
from typing import List, Optional

@dataclass
class KPISummaryDTO:
    total_projects: int
    total_drawings: int
    total_comments: int
    total_pages: int
    accuracy_rate: Optional[float]
    approved_count: int
    rejected_count: int
    pending_count: int
    flagged_count: int
    avg_confidence: float
    high_confidence_pct: float
    low_confidence_pct: float

@dataclass
class CategoryDistributionDTO:
    category_name: str
    count: int
    percentage: float
    color_hex: str = '#6366F1'

@dataclass
class ConfidenceBucketDTO:
    range_label: str
    count: int
    percentage: float

@dataclass
class ReviewerMetricsDTO:
    reviewer_id: str
    reviewer_name: str
    comments_reviewed: int
    approved: int
    rejected: int
    flagged: int
    avg_review_time_hours: Optional[float] = None

@dataclass
class TrendDataPointDTO:
    period_label: str
    count: int

@dataclass
class ProjectAnalyticsDTO:
    project_id: str
    project_name: str
    kpi_summary: KPISummaryDTO
    category_distribution: List[CategoryDistributionDTO]
    confidence_distribution: List[ConfidenceBucketDTO]
    status_trend: List[TrendDataPointDTO]
    reviewer_metrics: List[ReviewerMetricsDTO]
