"""
Unit tests for core/models.py — Pydantic v2 compatibility.
"""

import pytest
from datetime import datetime, timedelta
from core.models import (
    ActionSchema, AnalysisRequestSchema, ReportSchema,
    MetricToWatchSchema, GoalType, PriorityLevel, EffortLevel,
)


class TestActionSchema:
    """Test ActionSchema Pydantic model."""

    def test_action_schema_creation(self):
        """Test basic ActionSchema instantiation."""
        action = ActionSchema(
            id="test_001",
            description="Test action",
            priority=PriorityLevel.HIGH,
            effort=EffortLevel.LOW,
            expected_impact_metric="CTR +10%",
            rationale="Because it works",
        )
        assert action.id == "test_001"
        assert action.priority == "high"
        assert action.effort == "low"
        assert action.budget_required is None

    def test_action_schema_uses_enum_values(self):
        """Enum fields must be serialised as plain strings (use_enum_values=True)."""
        action = ActionSchema(
            id="test_002",
            description="Another action",
            priority=PriorityLevel.CRITICAL,
            effort=EffortLevel.HIGH,
            expected_impact_metric="Watch time",
            rationale="Critical path",
        )
        data = action.model_dump()
        assert data["priority"] == "critical"
        assert data["effort"] == "high"

    def test_action_schema_with_budget(self):
        """Test ActionSchema with an optional budget_required field."""
        action = ActionSchema(
            id="test_003",
            description="Paid action",
            priority=PriorityLevel.MEDIUM,
            effort=EffortLevel.MEDIUM,
            expected_impact_metric="Subscribers",
            rationale="Needs budget",
            budget_required=250.0,
        )
        assert action.budget_required == 250.0


class TestAnalysisRequestSchema:
    """Test AnalysisRequestSchema Pydantic model."""

    def test_defaults(self):
        """Test default values for timeframe and budget."""
        schema = AnalysisRequestSchema(goal=GoalType.GROW_SUBSCRIBERS)
        assert schema.timeframe == 30
        assert schema.budget == 0.0

    def test_uses_enum_values(self):
        """GoalType must be serialised as a plain string."""
        schema = AnalysisRequestSchema(goal=GoalType.INCREASE_CTR, timeframe=7, budget=100)
        data = schema.model_dump()
        assert data["goal"] == "increase_ctr"

    def test_custom_values(self):
        """Test passing custom timeframe and budget."""
        schema = AnalysisRequestSchema(
            goal=GoalType.BOOST_WATCH_TIME,
            timeframe=14,
            budget=500.0,
        )
        assert schema.timeframe == 14
        assert schema.budget == 500.0


class TestReportSchema:
    """Test ReportSchema Pydantic model."""

    def test_report_schema_creation(self):
        """Test creating a full ReportSchema."""
        now = datetime.utcnow()
        action = ActionSchema(
            id="r_001",
            description="Action",
            priority=PriorityLevel.HIGH,
            effort=EffortLevel.LOW,
            expected_impact_metric="Subs",
            rationale="Test",
        )
        metric = MetricToWatchSchema(metric="ctr", target="+5%", period="7 days")
        report = ReportSchema(
            goal="grow_subscribers",
            diagnosis="Looking good",
            actions=[action],
            metrics_to_watch=[metric],
            created_at=now,
            expires_at=now + timedelta(days=7),
        )
        assert report.goal == "grow_subscribers"
        assert len(report.actions) == 1
        assert len(report.metrics_to_watch) == 1
