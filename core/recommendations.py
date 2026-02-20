"""
Recommendations Module: Convert insights into prioritized actions.
Generates 3-5 actionable recommendations with effort/priority/impact estimates.
"""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class Priority(str, Enum):
    """Action priority levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class Effort(str, Enum):
    """Implementation effort required."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

@dataclass
class Action:
    """A single recommended action."""
    id: str
    description: str
    priority: Priority
    effort: Effort
    expected_impact_metric: str
    rationale: str
    budget_required: Optional[float] = None
    implementation_steps: Optional[List[str]] = None

@dataclass
class RecommendationRequest:
    """Request to generate recommendations from insights."""
    insights: Dict[str, Any]  # From analysis module
    goal: str  # grow_subscribers | increase_ctr | boost_watch_time
    budget: float
    llm_model: str = "gpt-4o"

class RecommendationGenerator:
    """Generates prioritized actions from insights."""

    _PRIORITY_ORDER = {Priority.CRITICAL: 0, Priority.HIGH: 1, Priority.MEDIUM: 2, Priority.LOW: 3}

    def __init__(self):
        self.goal_templates = {
            'grow_subscribers': self._recommend_growth,
            'increase_ctr': self._recommend_ctr,
            'boost_watch_time': self._recommend_watch_time,
        }
    
    def run(self, request: RecommendationRequest) -> List[Action]:
        """Generate recommendations for a goal."""
        logger.info(f"Generating recommendations for goal: {request.goal}")
        
        if request.goal not in self.goal_templates:
            raise ValueError(f"Unknown goal: {request.goal}")
        
        # Generate base recommendations
        actions = self.goal_templates[request.goal](request.insights, request.budget)
        
        # Sort by priority and budget constraints
        actions = self._prioritize_actions(actions, request.budget)
        
        # Limit to 5 actions
        actions = actions[:5]
        
        logger.info(f"Generated {len(actions)} recommendations")
        return actions
    
    def _recommend_growth(self, insights: Dict[str, Any], budget: float) -> List[Action]:
        """Generate growth-focused recommendations."""
        actions = [
            Action(
                id="gr_001",
                description="Analyze top 10% videos for common patterns (topic, length, thumbnail style)",
                priority=Priority.HIGH,
                effort=Effort.LOW,
                expected_impact_metric="Content clarity",
                rationale="Understanding what works informs future content strategy",
                budget_required=0
            ),
            Action(
                id="gr_002",
                description="Test consistent upload schedule (2x/week minimum)",
                priority=Priority.HIGH,
                effort=Effort.MEDIUM,
                expected_impact_metric="Subscriber retention +5-10%",
                rationale="Algorithm favors consistency; audience learns when to expect content",
                budget_required=0
            ),
            Action(
                id="gr_003",
                description="Create community posts between video uploads (1-2x/week)",
                priority=Priority.MEDIUM,
                effort=Effort.LOW,
                expected_impact_metric="Engagement +3-8%",
                rationale="Keeps community active, boosts algorithm signal",
                budget_required=0
            ),
            Action(
                id="gr_004",
                description="Optimize video titles for search (include top keywords)",
                priority=Priority.MEDIUM,
                effort=Effort.MEDIUM,
                expected_impact_metric="Organic views +15-20%",
                rationale="Better discoverability through YouTube search",
                budget_required=0
            ),
            Action(
                id="gr_005",
                description="A/B test thumbnail styles with 2-3 variations per video",
                priority=Priority.MEDIUM,
                effort=Effort.HIGH,
                expected_impact_metric="CTR +5-15%",
                rationale="Thumbnails heavily influence click-through rate",
                budget_required=50 if budget >= 50 else 0
            )
        ]
        return actions
    
    def _recommend_ctr(self, insights: Dict[str, Any], budget: float) -> List[Action]:
        """Generate CTR-focused recommendations."""
        actions = [
            Action(
                id="ctr_001",
                description="Redesign thumbnails: high contrast, large text, facial expressions",
                priority=Priority.HIGH,
                effort=Effort.MEDIUM,
                expected_impact_metric="CTR +10-20%",
                rationale="High-impact visual elements increase click probability",
                budget_required=0
            ),
            Action(
                id="ctr_002",
                description="A/B test 3-5 title variations (hook vs descriptive)",
                priority=Priority.HIGH,
                effort=Effort.LOW,
                expected_impact_metric="CTR +5-15%",
                rationale="Title is first thing viewers read before deciding to click",
                budget_required=0
            ),
            Action(
                id="ctr_003",
                description="Optimize video positioning: move key hooks to first 3 seconds",
                priority=Priority.MEDIUM,
                effort=Effort.MEDIUM,
                expected_impact_metric="Retention +3-8%",
                rationale="Viewers decide to click based on preview context",
                budget_required=0
            ),
            Action(
                id="ctr_004",
                description="Test call-to-action placement in thumbnails",
                priority=Priority.MEDIUM,
                effort=Effort.LOW,
                expected_impact_metric="CTR +2-8%",
                rationale="Subtle CTA elements guide viewer attention",
                budget_required=0
            )
        ]
        return actions
    
    def _recommend_watch_time(self, insights: Dict[str, Any], budget: float) -> List[Action]:
        """Generate watch-time-focused recommendations."""
        actions = [
            Action(
                id="wt_001",
                description="Optimize pacing: tighten script, remove dead air (edit tighter)",
                priority=Priority.HIGH,
                effort=Effort.HIGH,
                expected_impact_metric="Watch time +10-15%",
                rationale="Viewers abandon slow content; tighter pacing holds attention",
                budget_required=0
            ),
            Action(
                id="wt_002",
                description="Add pattern interrupts every 15-30 seconds (B-roll, graphics, zoom)",
                priority=Priority.HIGH,
                effort=Effort.MEDIUM,
                expected_impact_metric="Retention +8-12%",
                rationale="Visual variety prevents attention drop-off",
                budget_required=0
            ),
            Action(
                id="wt_003",
                description="Place key information in middle-to-end of video (after retention dip)",
                priority=Priority.MEDIUM,
                effort=Effort.LOW,
                expected_impact_metric="Watch time +3-8%",
                rationale="Hooks front-loaders; structure keeps viewers through full content",
                budget_required=0
            ),
            Action(
                id="wt_004",
                description="Add end screens with next video suggestion (increase series)",
                priority=Priority.MEDIUM,
                effort=Effort.LOW,
                expected_impact_metric="Session watch time +15-25%",
                rationale="Series format increases total session watch time",
                budget_required=0
            ),
            Action(
                id="wt_005",
                description="Test optimal video length (compare 5min, 10min, 15min versions)",
                priority=Priority.LOW,
                effort=Effort.HIGH,
                expected_impact_metric="Benchmark for audience preference",
                rationale="Different content types perform better at different lengths",
                budget_required=0
            )
        ]
        return actions
    
    def _prioritize_actions(self, actions: List[Action], budget: float) -> List[Action]:
        """Sort and filter actions by priority and budget."""
        # Filter by budget
        affordable = [a for a in actions if (a.budget_required or 0) <= budget]
        
        # Sort by priority (high → medium → low)
        affordable.sort(key=lambda a: self._PRIORITY_ORDER.get(a.priority, 4))
        
        return affordable

# Singleton instance
recommendation_generator = RecommendationGenerator()

def recommend(request: RecommendationRequest) -> List[Action]:
    """Public API for recommendations."""
    return recommendation_generator.run(request)
