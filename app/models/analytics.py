"""Analytics and statistics models for admin dashboard."""

from sqlmodel import SQLModel


class OverviewStats(SQLModel):
    """Overview statistics for admin dashboard."""

    total_validated_associations: int
    total_completed_missions: int
    total_users: int
    pending_reports_count: int
    pending_associations_count: int


class MonthlyDataPoint(SQLModel):
    """Monthly data point for chart visualization."""

    month: str  # Format: "YYYY-MM"
    value: int


class ReportStats(SQLModel):
    """Report statistics by processing state."""

    pending: int
    accepted: int
    rejected: int
