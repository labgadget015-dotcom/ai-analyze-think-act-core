"""
Data Models: Pydantic schemas for API validation and serialization.
"""

from pydantic import BaseModel, ConfigDict, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum

class GoalType(str, Enum):
    GROW_SUBSCRIBERS = "grow_subscribers"
    INCREASE_CTR = "increase_ctr"
    BOOST_WATCH_TIME = "boost_watch_time"

class PriorityLevel(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class EffortLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class ActionSchema(BaseModel):
    """Single recommended action."""
    model_config = ConfigDict(use_enum_values=True)

    id: str = Field(..., description="Unique action identifier")
    description: str = Field(..., description="What to do")
    priority: PriorityLevel
    effort: EffortLevel
    expected_impact_metric: str = Field(..., description="Metric expected to improve")
    rationale: str = Field(..., description="Why this action matters")
    budget_required: Optional[float] = None

class MetricToWatchSchema(BaseModel):
    """Key metric to track."""
    metric: str
    target: str
    period: str

class ReportSchema(BaseModel):
    """Analysis report output."""
    goal: str
    diagnosis: str = Field(..., description="Natural language summary")
    actions: List[ActionSchema]
    metrics_to_watch: List[MetricToWatchSchema]
    created_at: datetime
    expires_at: datetime

class AnalysisRequestSchema(BaseModel):
    """Request for analysis."""
    model_config = ConfigDict(use_enum_values=True)

    goal: GoalType
    timeframe: int = Field(default=30, description="Days to analyze")
    budget: float = Field(default=0, description="Budget in USD")

class UserChannelSchema(BaseModel):
    """User's connected channel."""
    user_id: str
    channel_id: str
    channel_name: str
    platform: str = "youtube"
    connected_at: datetime
    last_analysis: Optional[datetime] = None

class PipelineStatusSchema(BaseModel):
    """Status of analysis pipeline."""
    pipeline_id: str
    status: str  # running | completed | failed
    progress: int  # 0-100
    last_updated: datetime
    errors: List[str] = []
