"""
Performance benchmarks for the AI Analyze-Think-Act core pipeline.

These tests measure latency and throughput of the key pipeline stages to
establish a baseline for the <2 min per full analysis run target.

Tests are annotated with loose upper-bound assertions (×10 safety margin over
typical local execution time) so they pass reliably in CI while still catching
catastrophic regressions.
"""

import time
from datetime import datetime
from typing import List

import pandas as pd
import pytest

from core.analysis import AnalysisRequest, AnalysisPipeline
from core.ingest import IngestConfig, IngestPipeline
from core.orchestration import ChainConfig, PromptChainOrchestrator, PromptStage
from core.recommendations import RecommendationRequest, RecommendationGenerator
from core.token_optimizer import TokenOptimizer, TokenBudget, estimate_tokens, estimate_cost


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_dataset(rows: int = 100) -> pd.DataFrame:
    """Build a synthetic YouTube-style dataset for benchmarking."""
    import random
    random.seed(42)
    return pd.DataFrame({
        "video_id": [f"v{i:04d}" for i in range(rows)],
        "views": [random.randint(100, 100_000) for _ in range(rows)],
        "subscribers_gained": [random.randint(0, 500) for _ in range(rows)],
        "ctr": [round(random.uniform(2.0, 12.0), 2) for _ in range(rows)],
        "avg_view_duration": [round(random.uniform(1.5, 15.0), 2) for _ in range(rows)],
        "watch_time": [round(random.uniform(10.0, 5000.0), 1) for _ in range(rows)],
    })


def _elapsed_ms(start: float) -> float:
    return (time.monotonic() - start) * 1000


# ---------------------------------------------------------------------------
# Token optimizer benchmarks
# ---------------------------------------------------------------------------

class TestTokenOptimizerPerformance:
    def test_estimate_tokens_throughput(self):
        """estimate_tokens should handle 10,000 calls in under 100 ms."""
        text = "A " * 500  # ~1000 chars
        start = time.monotonic()
        for _ in range(10_000):
            estimate_tokens(text)
        elapsed = _elapsed_ms(start)
        assert elapsed < 100, f"estimate_tokens 10k calls took {elapsed:.1f}ms (limit 100ms)"

    def test_estimate_cost_throughput(self):
        """estimate_cost should handle 10,000 calls in under 100 ms."""
        start = time.monotonic()
        for _ in range(10_000):
            estimate_cost(1000, 500, "gpt-4o")
        elapsed = _elapsed_ms(start)
        assert elapsed < 100, f"estimate_cost 10k calls took {elapsed:.1f}ms (limit 100ms)"

    def test_optimizer_prepare_latency(self):
        """TokenOptimizer.prepare should complete in under 5 ms per call."""
        optimizer = TokenOptimizer(budget=TokenBudget(model="gpt-4o"))
        prompt = "Analyze the following YouTube channel data: " + ("sample data " * 100)
        start = time.monotonic()
        for _ in range(100):
            safe, record = optimizer.prepare(stage="trend", prompt=prompt)
        elapsed = _elapsed_ms(start)
        per_call = elapsed / 100
        assert per_call < 5, f"TokenOptimizer.prepare avg {per_call:.2f}ms per call (limit 5ms)"


# ---------------------------------------------------------------------------
# Orchestration benchmarks
# ---------------------------------------------------------------------------

class TestOrchestrationPerformance:
    def _make_fast_caller(self):
        """Return a minimal LLM caller with no I/O overhead."""
        def caller(prompt, model, max_tokens):
            return '{"benchmark": true, "stage": "ok"}'
        return caller

    def test_single_stage_chain_latency(self):
        """A single-stage chain should complete in under 50 ms (stub LLM)."""
        orch = PromptChainOrchestrator(llm_caller=self._make_fast_caller())
        config = ChainConfig(
            goal="grow_subscribers",
            stages=[PromptStage(name="trend", prompt_template="Analyze {dataset}")],
        )
        start = time.monotonic()
        result = orch.run(config, context={"dataset": "[]"})
        elapsed = _elapsed_ms(start)
        assert result.succeeded()
        assert elapsed < 50, f"Single-stage chain took {elapsed:.1f}ms (limit 50ms)"

    def test_three_stage_chain_latency(self):
        """A three-stage chain should complete in under 100 ms (stub LLM)."""
        orch = PromptChainOrchestrator(llm_caller=self._make_fast_caller())
        config = ChainConfig(
            goal="grow_subscribers",
            stages=[
                PromptStage(name="trend", prompt_template="Trend: {dataset}"),
                PromptStage(name="ranking", prompt_template="Rank: {trend_result}"),
                PromptStage(name="prediction", prompt_template="Predict: {ranking_result}"),
            ],
        )
        start = time.monotonic()
        result = orch.run(config, context={"dataset": "[]"})
        elapsed = _elapsed_ms(start)
        assert len(result.stage_results) == 3
        assert elapsed < 100, f"Three-stage chain took {elapsed:.1f}ms (limit 100ms)"

    def test_chain_throughput(self):
        """Should complete 50 single-stage chain runs in under 2000 ms (stub LLM)."""
        orch = PromptChainOrchestrator(llm_caller=self._make_fast_caller())
        config = ChainConfig(
            goal="increase_ctr",
            stages=[PromptStage(name="anomaly", prompt_template="Detect anomalies: {dataset}")],
        )
        start = time.monotonic()
        for _ in range(50):
            orch.run(config, context={"dataset": "[]"})
        elapsed = _elapsed_ms(start)
        assert elapsed < 2000, f"50 chain runs took {elapsed:.1f}ms (limit 2000ms)"


# ---------------------------------------------------------------------------
# Analysis pipeline benchmarks
# ---------------------------------------------------------------------------

class TestAnalysisPipelinePerformance:
    def test_grow_subscribers_latency(self):
        """grow_subscribers analysis should complete in under 500 ms (stub LLM)."""
        df = _make_dataset(100)
        request = AnalysisRequest(
            dataset=df,
            goal="grow_subscribers",
            constraints={"budget": 500, "timeframe_days": 30},
        )
        pipeline = AnalysisPipeline()
        start = time.monotonic()
        result = pipeline.run(request)
        elapsed = _elapsed_ms(start)
        assert result.goal == "grow_subscribers"
        assert elapsed < 500, f"grow_subscribers analysis took {elapsed:.1f}ms (limit 500ms)"

    def test_increase_ctr_latency(self):
        """increase_ctr analysis should complete in under 500 ms (stub LLM)."""
        df = _make_dataset(50)
        request = AnalysisRequest(
            dataset=df,
            goal="increase_ctr",
            constraints={"budget": 200, "timeframe_days": 7},
        )
        pipeline = AnalysisPipeline()
        start = time.monotonic()
        result = pipeline.run(request)
        elapsed = _elapsed_ms(start)
        assert result.goal == "increase_ctr"
        assert elapsed < 500, f"increase_ctr analysis took {elapsed:.1f}ms (limit 500ms)"

    def test_boost_watch_time_latency(self):
        """boost_watch_time analysis should complete in under 500 ms (stub LLM)."""
        df = _make_dataset(50)
        request = AnalysisRequest(
            dataset=df,
            goal="boost_watch_time",
            constraints={"budget": 500, "timeframe_days": 14},
        )
        pipeline = AnalysisPipeline()
        start = time.monotonic()
        result = pipeline.run(request)
        elapsed = _elapsed_ms(start)
        assert result.goal == "boost_watch_time"
        assert elapsed < 500, f"boost_watch_time analysis took {elapsed:.1f}ms (limit 500ms)"

    def test_large_dataset_latency(self):
        """Analysis on a 1,000-row dataset should complete in under 2000 ms."""
        df = _make_dataset(1000)
        request = AnalysisRequest(
            dataset=df,
            goal="grow_subscribers",
            constraints={"budget": 500, "timeframe_days": 90},
        )
        pipeline = AnalysisPipeline()
        start = time.monotonic()
        result = pipeline.run(request)
        elapsed = _elapsed_ms(start)
        assert result.goal == "grow_subscribers"
        assert elapsed < 2000, f"1000-row analysis took {elapsed:.1f}ms (limit 2000ms)"


# ---------------------------------------------------------------------------
# Recommendations performance
# ---------------------------------------------------------------------------

class TestRecommendationsPerformance:
    def test_recommendations_latency(self):
        """RecommendationGenerator should complete in under 10 ms."""
        gen = RecommendationGenerator()
        start = time.monotonic()
        for _ in range(100):
            gen.run(RecommendationRequest(
                insights={},
                goal="grow_subscribers",
                budget=500,
            ))
        elapsed = _elapsed_ms(start)
        per_call = elapsed / 100
        assert per_call < 10, f"Recommendations avg {per_call:.2f}ms per call (limit 10ms)"


# ---------------------------------------------------------------------------
# Full pipeline benchmark
# ---------------------------------------------------------------------------

class TestFullPipelinePerformance:
    def test_full_pipeline_under_two_minutes(self):
        """
        The complete ingest → analyze → recommend pipeline should run in well
        under the 2-minute target (stub LLM, no network I/O).
        """
        # Ingest
        ingest_config = IngestConfig(
            source_type="youtube",
            auth_token="bench_token",
            timeframe={"start": datetime.now(), "end": datetime.now()},
        )
        ingest_start = time.monotonic()
        ingest_pipeline = IngestPipeline()
        dataset = ingest_pipeline.run(ingest_config)
        ingest_ms = _elapsed_ms(ingest_start)

        # Use synthetic data since stub returns empty DataFrame
        dataset = _make_dataset(100)

        # Analyze
        analysis_start = time.monotonic()
        analysis_req = AnalysisRequest(
            dataset=dataset,
            goal="grow_subscribers",
            constraints={"budget": 500, "timeframe_days": 30},
        )
        pipeline = AnalysisPipeline()
        analysis_result = pipeline.run(analysis_req)
        analysis_ms = _elapsed_ms(analysis_start)

        # Recommend
        rec_start = time.monotonic()
        rec_req = RecommendationRequest(
            insights={"analysis": analysis_result},
            goal="grow_subscribers",
            budget=500,
        )
        gen = RecommendationGenerator()
        recommendations = gen.run(rec_req)
        rec_ms = _elapsed_ms(rec_start)

        total_ms = ingest_ms + analysis_ms + rec_ms
        total_seconds = total_ms / 1000

        # Assertions
        assert analysis_result.goal == "grow_subscribers"
        assert len(recommendations) > 0
        # Well under 2 minutes (120 s) — with stub LLM should be <1s
        assert total_seconds < 120, (
            f"Full pipeline took {total_seconds:.2f}s "
            f"(ingest={ingest_ms:.0f}ms, analysis={analysis_ms:.0f}ms, rec={rec_ms:.0f}ms)"
        )
