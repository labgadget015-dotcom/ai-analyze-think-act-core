"""
Analysis Module: Trend, anomaly, ranking, and prediction analysis.
Orchestrates multi-layer LLM prompts for insight generation.
"""

import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import pandas as pd

from .orchestration import ChainConfig, PromptChainOrchestrator, PromptStage, _stub_llm_caller
from .token_optimizer import TokenBudget

logger = logging.getLogger(__name__)


@dataclass
class AnalysisRequest:
    """Request configuration for analysis."""
    dataset: pd.DataFrame
    goal: str  # grow_subscribers | increase_ctr | boost_watch_time
    constraints: Dict[str, Any]  # {budget, timeframe_days}
    llm_model: str = "gpt-4o"
    context: Optional[str] = None


@dataclass
class AnalysisResult:
    """Result of analysis containing all insights."""
    goal: str
    trends: List[Dict[str, Any]]
    anomalies: List[Dict[str, Any]]
    rankings: List[Dict[str, Any]]
    predictions: Optional[List[Dict[str, Any]]] = None
    diagnosis: str = ""
    metrics_to_watch: Optional[List[Dict[str, Any]]] = None


# ---------------------------------------------------------------------------
# Prompt template loading (lazy — avoids hard import-time dependency on yaml)
# ---------------------------------------------------------------------------

def _load_goal_prompts(goal: str) -> Dict[str, str]:
    """Load per-stage prompt templates for *goal* from youtube_goals.yaml."""
    try:
        from prompts import get_prompt_for_goal
        block = get_prompt_for_goal(goal, domain="youtube")
        return {
            key: value
            for key, value in block.items()
            if key.endswith("_prompt")
        }
    except Exception as exc:
        logger.debug("Could not load YAML prompts for goal '%s': %s", goal, exc)
        return {}


def _build_prompt_stages(chain: List[str], prompts: Dict[str, str]) -> List[PromptStage]:
    """Convert a chain definition + prompt map into PromptStage objects."""
    stages = []
    for stage_name in chain:
        template = prompts.get(f"{stage_name}_prompt", f"Analyze data for stage: {stage_name}. Data: {{dataset}}")
        stages.append(PromptStage(name=stage_name, prompt_template=template, required=False))
    return stages


# ---------------------------------------------------------------------------
# Result parsing helpers
# ---------------------------------------------------------------------------

def _parse_stage_response(response: Any, stage: str) -> List[Dict[str, Any]]:
    """
    Try to parse a JSON LLM response into a list of insight dicts.
    Falls back to a single-item list wrapping the raw response when parsing fails.
    """
    if response is None:
        return []
    try:
        parsed = json.loads(str(response)) if isinstance(response, str) else response
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict):
            # Unwrap common envelope keys
            for key in (stage, f"{stage}_analysis", "items", "results", "data"):
                if key in parsed and isinstance(parsed[key], list):
                    return parsed[key]
            return [parsed]
    except (json.JSONDecodeError, TypeError):
        pass
    return [{"raw": str(response), "stage": stage}]


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

class AnalysisPipeline:
    """Orchestrates multi-stage analysis with LLM prompt chains."""

    def __init__(self, orchestrator: Optional[PromptChainOrchestrator] = None):
        # Goal → ordered list of stage names
        self.goal_chains: Dict[str, List[str]] = {
            "grow_subscribers": ["trend", "ranking", "prediction"],
            "increase_ctr": ["anomaly", "ranking"],
            "boost_watch_time": ["trend", "prediction"],
        }

        # Keep stub stage handlers for offline / test use
        self.analysis_stages = {
            "trend": self._analyze_trends,
            "anomaly": self._detect_anomalies,
            "ranking": self._rank_items,
            "prediction": self._predict_future,
        }

        self._orchestrator = orchestrator or PromptChainOrchestrator()

    def run(self, request: AnalysisRequest) -> AnalysisResult:
        """Execute the analysis pipeline for a goal."""
        logger.info("Starting analysis for goal: %s", request.goal)

        if request.goal not in self.goal_chains:
            raise ValueError(f"Unknown goal: {request.goal}")

        chain = self.goal_chains[request.goal]
        budget = TokenBudget(
            model=request.llm_model,
            max_cost_usd=float(request.constraints.get("budget", 0)) or None,
        )

        # Build prompt stages from YAML templates (falls back to simple defaults)
        prompts = _load_goal_prompts(request.goal)
        stages = _build_prompt_stages(chain, prompts)

        # Prepare context for template rendering
        timeframe_days = request.constraints.get("timeframe_days", 30)
        context: Dict[str, Any] = {
            "dataset": request.dataset.to_json(orient="records", date_format="iso")
            if not request.dataset.empty else "[]",
            "timeframe_days": timeframe_days,
            "video_data": request.dataset.to_json(orient="records", date_format="iso")
            if not request.dataset.empty else "[]",
            "historical_data": request.dataset.to_json(orient="records", date_format="iso")
            if not request.dataset.empty else "[]",
            "current_metrics": f"records={len(request.dataset)}",
            "avg_ctr": request.dataset["ctr"].mean()
            if "ctr" in request.dataset.columns else "N/A",
            "avg_view_duration": request.dataset["avg_view_duration"].mean()
            if "avg_view_duration" in request.dataset.columns else "N/A",
            "total_watch_hours": request.dataset["watch_time"].sum()
            if "watch_time" in request.dataset.columns else "N/A",
            "current_subscribers": (
                request.dataset["subscribers"].sum()
                if "subscribers" in request.dataset.columns
                else request.dataset["subscribers_gained"].sum()
                if "subscribers_gained" in request.dataset.columns
                else "N/A"
            ),
            "retention_data": "N/A",
            "content_plan": "N/A",
        }

        config = ChainConfig(goal=request.goal, stages=stages, budget=budget)
        chain_result = self._orchestrator.run(config, context=context)

        # Collect results from orchestrator; fall back to stubs for stages that
        # returned a stub response (no real LLM configured)
        results: Dict[str, List[Dict[str, Any]]] = {}
        for stage_result in chain_result.stage_results:
            stage_name = stage_result.stage
            is_stub = (
                not stage_result.success
                or (isinstance(stage_result.response, str) and '"stub": true' in stage_result.response)
            )
            if is_stub:
                # Fall back to deterministic stub
                results[stage_name] = self.analysis_stages[stage_name](request.dataset, request.goal)
            else:
                results[stage_name] = _parse_stage_response(stage_result.response, stage_name)

        analysis_result = AnalysisResult(
            goal=request.goal,
            trends=results.get("trend", []),
            anomalies=results.get("anomaly", []),
            rankings=results.get("ranking", []),
            predictions=results.get("prediction", None),
            diagnosis=self._generate_diagnosis(results, request.goal),
            metrics_to_watch=self._identify_metrics(request.goal),
        )

        logger.info("Analysis complete for %s", request.goal)
        return analysis_result

    # ------------------------------------------------------------------
    # Stub stage implementations (used when no LLM is configured)
    # ------------------------------------------------------------------

    def _analyze_trends(self, data: pd.DataFrame, goal: str) -> List[Dict[str, Any]]:
        """Identify trends in the dataset."""
        if len(data) == 0:
            return []
        return [
            {
                "insight": f"Dataset contains {len(data)} records over analysis period",
                "data_point": f"Mean record count: {len(data)}",
                "confidence": "high",
            }
        ]

    def _detect_anomalies(self, data: pd.DataFrame, goal: str) -> List[Dict[str, Any]]:
        """Detect anomalies in the data."""
        return [
            {
                "item_id": "sample_001",
                "metric": "engagement_rate",
                "deviation": 2.5,
                "direction": "above_average",
            }
        ]

    def _rank_items(self, data: pd.DataFrame, goal: str) -> List[Dict[str, Any]]:
        """Rank items by performance metric relevant to goal."""
        return [
            {"rank": 1, "item_id": "top_performer", "score": 9.5},
            {"rank": 2, "item_id": "second_best", "score": 8.2},
            {"rank": 3, "item_id": "third_place", "score": 7.8},
        ]

    def _predict_future(self, data: pd.DataFrame, goal: str) -> List[Dict[str, Any]]:
        """Predict future performance based on trends."""
        return [
            {
                "metric": "subscribers_next_week",
                "prediction": "+150",
                "confidence": "medium",
                "reasoning": "Based on current trajectory",
            }
        ]

    def _generate_diagnosis(self, results: Dict[str, Any], goal: str) -> str:
        """Generate natural language diagnosis from all insights."""
        diagnosis_stubs = {
            "grow_subscribers": "Channel engagement is stable. Subscriber growth slightly above average trend.",
            "increase_ctr": "Click-through rate shows potential with certain content types.",
            "boost_watch_time": "Average watch duration trending upward over analysis period.",
        }
        return diagnosis_stubs.get(goal, "Analysis complete.")

    def _identify_metrics(self, goal: str) -> List[Dict[str, Any]]:
        """Identify key metrics to watch based on goal."""
        metrics_map = {
            "grow_subscribers": [
                {"metric": "subs_gained", "target": "+50", "period": "7 days"},
                {"metric": "subscriber_retention", "target": "+3%", "period": "7 days"},
                {"metric": "engagement_rate", "target": "+5%", "period": "7 days"},
            ],
            "increase_ctr": [
                {"metric": "click_through_rate", "target": "+1.5%", "period": "7 days"},
                {"metric": "thumbnail_performance", "target": "baseline", "period": "7 days"},
                {"metric": "title_effectiveness", "target": "baseline", "period": "7 days"},
            ],
            "boost_watch_time": [
                {"metric": "avg_view_duration", "target": "+2min", "period": "7 days"},
                {"metric": "audience_retention", "target": "+5%", "period": "7 days"},
                {"metric": "video_completion_rate", "target": "+8%", "period": "7 days"},
            ],
        }
        return metrics_map.get(goal, [])


# Singleton instance
analysis_pipeline = AnalysisPipeline()


def analyze(request: AnalysisRequest) -> AnalysisResult:
    """Public API for analysis."""
    return analysis_pipeline.run(request)

