"""
AI Analyze->Think->Act Core Framework
Universal pipeline for AI-powered analysis, insights, and recommendations.
"""

__version__ = "0.1.0"
__author__ = "Gadget Lab"

from .ingest import ingest
from .analysis import analyze
from .recommendations import recommend
from .token_optimizer import TokenOptimizer, TokenBudget, estimate_tokens, estimate_cost
from .logging import PipelineMetricsCollector, get_json_logger, metrics
from .orchestration import PromptChainOrchestrator, ChainConfig, PromptStage, orchestrator

__all__ = [
    "ingest",
    "analyze",
    "recommend",
    "TokenOptimizer",
    "TokenBudget",
    "estimate_tokens",
    "estimate_cost",
    "PipelineMetricsCollector",
    "get_json_logger",
    "metrics",
    "PromptChainOrchestrator",
    "ChainConfig",
    "PromptStage",
    "orchestrator",
]
