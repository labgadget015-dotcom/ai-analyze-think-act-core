"""
Prompt Chain Orchestration.
Executes multi-stage LLM prompt chains with token optimization and structured
metrics logging.  Integrates core/token_optimizer.py and core/logging.py.
"""

import uuid
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from .token_optimizer import TokenBudget, TokenOptimizer
from .logging import PipelineMetricsCollector, PipelineRunMetric, metrics as default_metrics

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class PromptStage:
    """A single stage in a prompt chain."""
    name: str                            # e.g. "trend", "anomaly"
    prompt_template: str                 # String with {placeholder} slots
    handler: Optional[Callable] = None  # Optional post-processing callable
    required: bool = True               # If False, failures are non-fatal


@dataclass
class ChainConfig:
    """Configuration for a complete prompt chain."""
    goal: str
    stages: List[PromptStage]
    budget: Optional[TokenBudget] = None
    pipeline_id: Optional[str] = None   # Auto-generated if omitted


@dataclass
class StageResult:
    """Output from one executed stage."""
    stage: str
    prompt: str
    response: Any          # Raw LLM response (str) or post-processed output
    input_tokens: int
    output_tokens: int
    cost_usd: float
    truncated: bool = False
    success: bool = True
    error: Optional[str] = None


@dataclass
class ChainResult:
    """Full output from an executed prompt chain."""
    goal: str
    pipeline_id: str
    stage_results: List[StageResult] = field(default_factory=list)
    token_summary: Optional[Dict[str, Any]] = None
    run_metric: Optional[PipelineRunMetric] = None

    def get_stage(self, name: str) -> Optional[StageResult]:
        """Retrieve a stage result by name."""
        for r in self.stage_results:
            if r.stage == name:
                return r
        return None

    def succeeded(self) -> bool:
        return all(r.success for r in self.stage_results if r.success is not None)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class PromptChainOrchestrator:
    """
    Executes prompt chains stage-by-stage with token optimization, timing,
    and structured metrics logging.

    In production the *llm_caller* should be a function with signature::

        def call_llm(prompt: str, model: str, max_tokens: int) -> str: ...

    For testing / offline use the default stub returns a placeholder response.
    """

    def __init__(
        self,
        llm_caller: Optional[Callable] = None,
        metrics_collector: Optional[PipelineMetricsCollector] = None,
    ):
        self._llm_caller = llm_caller or _stub_llm_caller
        self._metrics = metrics_collector or default_metrics

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(
        self,
        config: ChainConfig,
        context: Optional[Dict[str, Any]] = None,
    ) -> ChainResult:
        """
        Execute all stages in *config.stages* in order.

        *context* is a dict of template variables used to format each stage's
        ``prompt_template``.  E.g. ``{"dataset": "...", "timeframe_days": 30}``.
        """
        pipeline_id = config.pipeline_id or f"run_{uuid.uuid4().hex[:8]}"
        context = context or {}
        budget = config.budget or TokenBudget()
        optimizer = TokenOptimizer(budget=budget)

        run = self._metrics.start_run(pipeline_id=pipeline_id, goal=config.goal)
        chain_result = ChainResult(
            goal=config.goal,
            pipeline_id=pipeline_id,
            run_metric=run,
        )

        logger.info(
            "Starting chain for goal '%s' with %d stage(s) [pipeline=%s]",
            config.goal,
            len(config.stages),
            pipeline_id,
        )

        overall_success = True

        for stage in config.stages:
            stage_result = self._execute_stage(
                stage=stage,
                context=context,
                optimizer=optimizer,
                run=run,
            )
            chain_result.stage_results.append(stage_result)

            # Propagate stage output into context for downstream stages
            if stage_result.success and stage_result.response is not None:
                context[f"{stage.name}_result"] = stage_result.response

            if not stage_result.success and stage.required:
                overall_success = False
                logger.error(
                    "Required stage '%s' failed — aborting chain [pipeline=%s]",
                    stage.name,
                    pipeline_id,
                )
                break

        token_summary = optimizer.get_summary().to_dict()
        chain_result.token_summary = token_summary

        self._metrics.finish_run(
            run=run,
            success=overall_success,
            token_summary=token_summary,
        )

        logger.info(
            "Chain complete for goal '%s': %d stages, $%.6f total [pipeline=%s]",
            config.goal,
            len(chain_result.stage_results),
            token_summary.get("total_cost_usd", 0),
            pipeline_id,
        )
        return chain_result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _execute_stage(
        self,
        stage: PromptStage,
        context: Dict[str, Any],
        optimizer: TokenOptimizer,
        run: PipelineRunMetric,
    ) -> StageResult:
        """Format, optimise, call LLM, and record metrics for one stage."""
        # Format prompt template with context variables (ignore missing keys)
        try:
            prompt = stage.prompt_template.format_map(_SafeDict(context))
        except Exception as exc:
            prompt = stage.prompt_template
            logger.debug("Prompt formatting failed for stage '%s': %s", stage.name, exc)

        # Apply token optimisation
        safe_prompt, token_record = optimizer.prepare(stage=stage.name, prompt=prompt)

        response = None
        error = None
        success = True

        with self._metrics.time_stage(run=run, stage=stage.name):
            try:
                raw_response = self._llm_caller(
                    prompt=safe_prompt,
                    model=optimizer.budget.model,
                    max_tokens=optimizer.budget.max_output_tokens,
                )
                # Post-process if a handler is provided
                response = stage.handler(raw_response) if stage.handler else raw_response
                output_tokens = len(str(response)) // 4  # simple estimate
                optimizer.record_actual(token_record, actual_output_tokens=output_tokens)
            except Exception as exc:
                error = str(exc)
                success = False
                output_tokens = 0
                optimizer.record_actual(token_record, actual_output_tokens=0)
                if stage.required:
                    raise

        return StageResult(
            stage=stage.name,
            prompt=safe_prompt,
            response=response,
            input_tokens=token_record.input_tokens,
            output_tokens=token_record.output_tokens,
            cost_usd=token_record.cost_usd,
            truncated=token_record.truncated,
            success=success,
            error=error,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _SafeDict(dict):
    """dict subclass that returns the key placeholder for missing keys."""

    def __missing__(self, key: str) -> str:
        return f"{{{key}}}"


def _stub_llm_caller(prompt: str, model: str, max_tokens: int) -> str:
    """
    Offline stub — returns a JSON-shaped placeholder.
    Replace with a real openai/anthropic/etc. call in production.
    """
    return (
        '{"stub": true, "message": "LLM not configured — replace _stub_llm_caller",'
        f' "model": "{model}", "prompt_length": {len(prompt)},'
        f' "max_tokens": {max_tokens}}}'
    )


# Module-level convenience instance (uses stub caller by default)
orchestrator = PromptChainOrchestrator()
