"""
Unit tests for core/token_optimizer.py
"""

import pytest
from core.token_optimizer import (
    estimate_tokens,
    estimate_cost,
    TokenBudget,
    TokenOptimizer,
    TokenUsageRecord,
    PipelineTokenSummary,
    MODEL_COSTS,
    MODEL_CONTEXT_LIMITS,
)


class TestEstimateTokens:
    def test_empty_string(self):
        assert estimate_tokens("") == 1  # min 1

    def test_short_text(self):
        # 4 chars = 1 token
        assert estimate_tokens("abcd") == 1

    def test_longer_text(self):
        text = "a" * 400
        assert estimate_tokens(text) == 100

    def test_scales_linearly(self):
        t1 = estimate_tokens("x" * 100)
        t2 = estimate_tokens("x" * 200)
        assert t2 == t1 * 2


class TestEstimateCost:
    def test_gpt4o_cost(self):
        cost = estimate_cost(1000, 500, "gpt-4o")
        rates = MODEL_COSTS["gpt-4o"]
        expected = rates["input"] + 0.5 * rates["output"]
        assert abs(cost - round(expected, 6)) < 1e-9

    def test_zero_tokens_returns_zero(self):
        assert estimate_cost(0, 0, "gpt-4o") == 0.0

    def test_unknown_model_falls_back_to_gpt4o(self):
        cost = estimate_cost(1000, 1000, "unknown-model")
        expected = estimate_cost(1000, 1000, "gpt-4o")
        assert cost == expected


class TestTokenBudget:
    def test_default_effective_limit(self):
        budget = TokenBudget(model="gpt-4o")
        assert budget.effective_input_limit() == MODEL_CONTEXT_LIMITS["gpt-4o"]

    def test_custom_limit_respected(self):
        budget = TokenBudget(model="gpt-4o", max_input_tokens=1000)
        assert budget.effective_input_limit() == 1000

    def test_cannot_exceed_model_limit(self):
        model_limit = MODEL_CONTEXT_LIMITS["gpt-3.5-turbo"]
        budget = TokenBudget(model="gpt-3.5-turbo", max_input_tokens=model_limit + 99999)
        assert budget.effective_input_limit() == model_limit


class TestPipelineTokenSummary:
    def _make_record(self, stage, inp, out, cost):
        return TokenUsageRecord(
            stage=stage, model="gpt-4o",
            input_tokens=inp, output_tokens=out,
            cost_usd=cost,
        )

    def test_empty_summary(self):
        summary = PipelineTokenSummary()
        assert summary.total_input_tokens == 0
        assert summary.total_output_tokens == 0
        assert summary.total_cost_usd == 0.0
        assert summary.total_tokens == 0

    def test_aggregation(self):
        summary = PipelineTokenSummary()
        summary.add(self._make_record("trend", 100, 50, 0.001))
        summary.add(self._make_record("ranking", 200, 80, 0.002))
        assert summary.total_input_tokens == 300
        assert summary.total_output_tokens == 130
        assert summary.total_tokens == 430
        assert abs(summary.total_cost_usd - 0.003) < 1e-9

    def test_to_dict_has_stages(self):
        summary = PipelineTokenSummary()
        summary.add(self._make_record("trend", 10, 5, 0.0001))
        d = summary.to_dict()
        assert "stages" in d
        assert d["stages"][0]["stage"] == "trend"


class TestTokenOptimizer:
    def test_prepare_no_truncation(self):
        optimizer = TokenOptimizer(budget=TokenBudget(max_input_tokens=10000))
        prompt = "Hello world"
        safe, record = optimizer.prepare("test", prompt)
        assert safe == prompt
        assert record.truncated is False

    def test_prepare_truncation(self):
        # Set a tiny limit
        budget = TokenBudget(model="gpt-4o", max_input_tokens=5)
        optimizer = TokenOptimizer(budget=budget)
        long_prompt = "a" * 200  # 50 tokens at 4 chars/token
        safe, record = optimizer.prepare("test", long_prompt)
        assert record.truncated is True
        assert len(safe) <= 5 * 4

    def test_record_actual_adds_to_summary(self):
        optimizer = TokenOptimizer()
        _, record = optimizer.prepare("trend", "some prompt text here")
        optimizer.record_actual(record, actual_output_tokens=100)
        assert optimizer.summary.total_output_tokens == 100
        assert optimizer.summary.total_cost_usd > 0

    def test_cost_check_with_budget(self):
        # Should not raise even when over budget (just warns)
        budget = TokenBudget(model="gpt-4o", max_cost_usd=0.000001)
        optimizer = TokenOptimizer(budget=budget)
        prompt = "This is a prompt " * 50
        safe, record = optimizer.prepare("trend", prompt)
        assert record is not None  # Does not raise

    def test_get_summary_returns_summary(self):
        optimizer = TokenOptimizer()
        summary = optimizer.get_summary()
        assert isinstance(summary, PipelineTokenSummary)
