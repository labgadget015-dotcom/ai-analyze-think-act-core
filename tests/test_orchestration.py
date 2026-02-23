"""
Unit tests for core/orchestration.py (prompt chain orchestrator)
"""

import pytest
from core.orchestration import (
    ChainConfig,
    ChainResult,
    PromptChainOrchestrator,
    PromptStage,
    StageResult,
    _stub_llm_caller,
)
from core.token_optimizer import TokenBudget
from core.logging import PipelineMetricsCollector


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_echo_caller(prefix="ECHO"):
    """LLM caller that echoes back the prompt length."""
    def caller(prompt, model, max_tokens):
        return f'{{"stub": true, "prefix": "{prefix}", "length": {len(prompt)}}}'
    return caller


def _make_failing_caller():
    """LLM caller that always raises."""
    def caller(prompt, model, max_tokens):
        raise RuntimeError("LLM unavailable")
    return caller


def _simple_chain(goal="test_goal", stages=None):
    if stages is None:
        stages = [
            PromptStage(name="trend", prompt_template="Analyze {dataset}"),
            PromptStage(name="ranking", prompt_template="Rank {trend_result}"),
        ]
    return ChainConfig(goal=goal, stages=stages)


# ---------------------------------------------------------------------------
# Tests: stub LLM caller
# ---------------------------------------------------------------------------

class TestStubLLMCaller:
    def test_returns_string(self):
        result = _stub_llm_caller("my prompt", "gpt-4o", 100)
        assert isinstance(result, str)
        assert "stub" in result

    def test_reflects_model(self):
        result = _stub_llm_caller("p", "gpt-4o-mini", 50)
        assert "gpt-4o-mini" in result


# ---------------------------------------------------------------------------
# Tests: PromptChainOrchestrator
# ---------------------------------------------------------------------------

class TestPromptChainOrchestrator:
    def test_run_returns_chain_result(self):
        orch = PromptChainOrchestrator(llm_caller=_make_echo_caller())
        config = _simple_chain()
        result = orch.run(config, context={"dataset": "sample data"})
        assert isinstance(result, ChainResult)
        assert result.goal == "test_goal"

    def test_stage_results_populated(self):
        orch = PromptChainOrchestrator(llm_caller=_make_echo_caller())
        config = _simple_chain()
        result = orch.run(config)
        assert len(result.stage_results) == 2
        assert result.stage_results[0].stage == "trend"
        assert result.stage_results[1].stage == "ranking"

    def test_all_stages_succeed(self):
        orch = PromptChainOrchestrator(llm_caller=_make_echo_caller())
        result = orch.run(_simple_chain())
        assert result.succeeded() is True

    def test_token_summary_present(self):
        orch = PromptChainOrchestrator(llm_caller=_make_echo_caller())
        result = orch.run(_simple_chain())
        assert result.token_summary is not None
        assert "total_tokens" in result.token_summary
        assert result.token_summary["total_tokens"] > 0

    def test_pipeline_id_auto_generated(self):
        orch = PromptChainOrchestrator(llm_caller=_make_echo_caller())
        result = orch.run(_simple_chain())
        assert result.pipeline_id.startswith("run_")

    def test_pipeline_id_respected_when_provided(self):
        orch = PromptChainOrchestrator(llm_caller=_make_echo_caller())
        config = _simple_chain()
        config.pipeline_id = "my_run_42"
        result = orch.run(config)
        assert result.pipeline_id == "my_run_42"

    def test_context_propagates_between_stages(self):
        """The output of stage N should be accessible in stage N+1 prompt."""
        captured_prompts = []

        def capturing_caller(prompt, model, max_tokens):
            captured_prompts.append(prompt)
            return '{"out": "value"}'

        stages = [
            PromptStage(name="trend", prompt_template="Step1: {dataset}"),
            PromptStage(name="ranking", prompt_template="Step2: {trend_result}"),
        ]
        orch = PromptChainOrchestrator(llm_caller=capturing_caller)
        orch.run(ChainConfig(goal="g", stages=stages), context={"dataset": "d"})
        # Second prompt should contain the output from the first stage
        assert len(captured_prompts) == 2
        assert '{"out": "value"}' in captured_prompts[1]

    def test_get_stage_by_name(self):
        orch = PromptChainOrchestrator(llm_caller=_make_echo_caller())
        result = orch.run(_simple_chain())
        trend = result.get_stage("trend")
        assert trend is not None
        assert trend.stage == "trend"

    def test_get_stage_missing_returns_none(self):
        orch = PromptChainOrchestrator(llm_caller=_make_echo_caller())
        result = orch.run(_simple_chain())
        assert result.get_stage("nonexistent") is None

    def test_required_stage_failure_aborts_chain(self):
        stages = [
            PromptStage(name="fail", prompt_template="p", required=True),
            PromptStage(name="after", prompt_template="p", required=False),
        ]
        orch = PromptChainOrchestrator(llm_caller=_make_failing_caller())
        with pytest.raises(RuntimeError):
            orch.run(ChainConfig(goal="g", stages=stages))

    def test_optional_stage_failure_does_not_abort(self):
        stages = [
            PromptStage(name="optional_fail", prompt_template="p", required=False),
            PromptStage(name="after", prompt_template="p", required=True),
        ]

        call_count = [0]

        def sometimes_fail(prompt, model, max_tokens):
            call_count[0] += 1
            if call_count[0] == 1:
                raise RuntimeError("optional failure")
            return '{"ok": true}'

        orch = PromptChainOrchestrator(llm_caller=sometimes_fail)
        result = orch.run(ChainConfig(goal="g", stages=stages))
        # Both stages should be recorded; optional one failed, required one succeeded
        assert len(result.stage_results) == 2
        assert result.stage_results[0].success is False
        assert result.stage_results[1].success is True

    def test_custom_budget_applied(self):
        budget = TokenBudget(model="gpt-4o-mini", max_output_tokens=100)
        orch = PromptChainOrchestrator(llm_caller=_make_echo_caller())
        config = _simple_chain()
        config.budget = budget
        result = orch.run(config)
        assert result.token_summary["stages"][0]["model"] == "gpt-4o-mini"

    def test_custom_metrics_collector_used(self):
        collector = PipelineMetricsCollector()
        orch = PromptChainOrchestrator(
            llm_caller=_make_echo_caller(),
            metrics_collector=collector,
        )
        result = orch.run(_simple_chain())
        assert result.run_metric is not None
        assert result.run_metric.goal == "test_goal"

    def test_prompt_handler_applied(self):
        def upper_handler(response):
            return response.upper()

        stages = [PromptStage(
            name="trend",
            prompt_template="Analyze {data}",
            handler=upper_handler,
        )]
        orch = PromptChainOrchestrator(llm_caller=_make_echo_caller())
        result = orch.run(ChainConfig(goal="g", stages=stages))
        assert result.stage_results[0].response == result.stage_results[0].response.upper()

    def test_single_stage_chain(self):
        stages = [PromptStage(name="only", prompt_template="Just do {task}")]
        orch = PromptChainOrchestrator(llm_caller=_make_echo_caller())
        result = orch.run(ChainConfig(goal="simple", stages=stages), context={"task": "x"})
        assert len(result.stage_results) == 1

    def test_empty_context_uses_placeholders(self):
        """Missing template variables should remain as {var} without raising."""
        stages = [PromptStage(name="s", prompt_template="data={missing_var}")]
        orch = PromptChainOrchestrator(llm_caller=_make_echo_caller())
        result = orch.run(ChainConfig(goal="g", stages=stages))
        assert "{missing_var}" in result.stage_results[0].prompt
