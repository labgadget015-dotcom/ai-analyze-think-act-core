"""
Token Optimizer: LLM cost and latency control.
Tracks token usage, estimates costs, and truncates prompts to stay within budgets.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

# Approximate cost per 1,000 tokens (input / output) in USD for common models
MODEL_COSTS: Dict[str, Dict[str, float]] = {
    "gpt-4o": {"input": 0.005, "output": 0.015},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
}

# Default context-window limits (tokens) per model
MODEL_CONTEXT_LIMITS: Dict[str, int] = {
    "gpt-4o": 128_000,
    "gpt-4o-mini": 128_000,
    "gpt-3.5-turbo": 16_385,
}

# Characters-per-token approximation (conservative for English text)
CHARS_PER_TOKEN = 4


def estimate_tokens(text: str) -> int:
    """Estimate token count from character count (conservative approximation)."""
    return max(1, len(text) // CHARS_PER_TOKEN)


def estimate_cost(input_tokens: int, output_tokens: int, model: str) -> float:
    """Estimate USD cost for a single LLM call."""
    rates = MODEL_COSTS.get(model, MODEL_COSTS["gpt-4o"])
    cost = (input_tokens / 1000) * rates["input"]
    cost += (output_tokens / 1000) * rates["output"]
    return round(cost, 6)


@dataclass
class TokenBudget:
    """Per-call token budget configuration."""
    model: str = "gpt-4o"
    max_input_tokens: Optional[int] = None   # None = use model limit
    max_output_tokens: int = 2000
    max_cost_usd: Optional[float] = None     # None = no cost cap

    def effective_input_limit(self) -> int:
        model_limit = MODEL_CONTEXT_LIMITS.get(self.model, 128_000)
        if self.max_input_tokens is None:
            return model_limit
        return min(self.max_input_tokens, model_limit)


@dataclass
class TokenUsageRecord:
    """Record of token usage for one LLM call."""
    stage: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    truncated: bool = False


@dataclass
class PipelineTokenSummary:
    """Aggregated token usage across a full pipeline run."""
    records: List[TokenUsageRecord] = field(default_factory=list)

    @property
    def total_input_tokens(self) -> int:
        return sum(r.input_tokens for r in self.records)

    @property
    def total_output_tokens(self) -> int:
        return sum(r.output_tokens for r in self.records)

    @property
    def total_cost_usd(self) -> float:
        return round(sum(r.cost_usd for r in self.records), 6)

    @property
    def total_tokens(self) -> int:
        return self.total_input_tokens + self.total_output_tokens

    def add(self, record: TokenUsageRecord) -> None:
        self.records.append(record)

    def to_dict(self) -> dict:
        return {
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_tokens,
            "total_cost_usd": self.total_cost_usd,
            "stages": [
                {
                    "stage": r.stage,
                    "model": r.model,
                    "input_tokens": r.input_tokens,
                    "output_tokens": r.output_tokens,
                    "cost_usd": r.cost_usd,
                    "truncated": r.truncated,
                }
                for r in self.records
            ],
        }


class TokenOptimizer:
    """
    Manages token budgets and optimizes prompts before sending to LLM.

    Usage::

        optimizer = TokenOptimizer(budget=TokenBudget(model="gpt-4o", max_cost_usd=0.10))
        safe_prompt, record = optimizer.prepare(stage="trend", prompt=raw_prompt)
        # ... call LLM with safe_prompt ...
        optimizer.record_actual(record, actual_output_tokens=350)
    """

    def __init__(self, budget: Optional[TokenBudget] = None):
        self.budget = budget or TokenBudget()
        self.summary = PipelineTokenSummary()

    def prepare(self, stage: str, prompt: str) -> tuple:
        """
        Truncate *prompt* if it exceeds the input token limit and return a
        (safe_prompt, TokenUsageRecord) tuple.  The record has a placeholder
        output_tokens=0 that should be updated after the real LLM response.
        """
        limit = self.budget.effective_input_limit()
        input_tokens = estimate_tokens(prompt)
        truncated = False

        if input_tokens > limit:
            # Truncate to fit: keep the first `limit` tokens worth of chars
            max_chars = limit * CHARS_PER_TOKEN
            prompt = prompt[:max_chars]
            input_tokens = limit
            truncated = True
            logger.warning(
                "Prompt for stage '%s' truncated to %d tokens (limit=%d)",
                stage,
                input_tokens,
                limit,
            )

        # Pre-flight cost check
        if self.budget.max_cost_usd is not None:
            projected = estimate_cost(
                input_tokens, self.budget.max_output_tokens, self.budget.model
            )
            remaining = self.budget.max_cost_usd - self.summary.total_cost_usd
            if projected > remaining:
                logger.warning(
                    "Stage '%s' projected cost $%.6f exceeds remaining budget $%.6f",
                    stage,
                    projected,
                    remaining,
                )

        record = TokenUsageRecord(
            stage=stage,
            model=self.budget.model,
            input_tokens=input_tokens,
            output_tokens=0,
            cost_usd=0.0,
            truncated=truncated,
        )
        return prompt, record

    def record_actual(self, record: TokenUsageRecord, actual_output_tokens: int) -> None:
        """Finalise a record with real output token count and add to summary."""
        record.output_tokens = actual_output_tokens
        record.cost_usd = estimate_cost(
            record.input_tokens, actual_output_tokens, record.model
        )
        self.summary.add(record)
        logger.debug(
            "Stage '%s': %d in + %d out = $%.6f",
            record.stage,
            record.input_tokens,
            actual_output_tokens,
            record.cost_usd,
        )

    def get_summary(self) -> PipelineTokenSummary:
        return self.summary
