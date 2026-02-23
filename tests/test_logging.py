"""
Unit tests for core/logging.py (pipeline metrics & JSON formatter)
"""

import json
import logging
import time

import pytest

from core.logging import (
    JSONFormatter,
    PipelineMetricsCollector,
    PipelineRunMetric,
    StageMetric,
    get_json_logger,
)


class TestJSONFormatter:
    def _make_record(self, message: str, level=logging.INFO) -> logging.LogRecord:
        record = logging.LogRecord(
            name="test", level=level,
            pathname="", lineno=0,
            msg=message, args=(), exc_info=None,
        )
        return record

    def test_output_is_valid_json(self):
        formatter = JSONFormatter()
        record = self._make_record("hello")
        output = formatter.format(record)
        parsed = json.loads(output)
        assert parsed["message"] == "hello"

    def test_output_has_required_fields(self):
        formatter = JSONFormatter()
        record = self._make_record("test msg", level=logging.WARNING)
        parsed = json.loads(formatter.format(record))
        assert "timestamp" in parsed
        assert "level" in parsed
        assert parsed["level"] == "WARNING"
        assert "logger" in parsed

    def test_get_json_logger_returns_logger(self):
        logger = get_json_logger("test.module")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test.module"

    def test_get_json_logger_not_duplicated(self):
        a = get_json_logger("same.logger")
        b = get_json_logger("same.logger")
        assert len(a.handlers) == len(b.handlers)


class TestPipelineMetricsCollector:
    def test_start_run_returns_run_metric(self):
        collector = PipelineMetricsCollector()
        run = collector.start_run(pipeline_id="p1", goal="grow_subscribers")
        assert isinstance(run, PipelineRunMetric)
        assert run.pipeline_id == "p1"
        assert run.goal == "grow_subscribers"
        assert run.started_at is not None

    def test_finish_run_sets_fields(self):
        collector = PipelineMetricsCollector()
        run = collector.start_run("p2", "increase_ctr")
        collector.finish_run(run, success=True, record_count=10)
        assert run.success is True
        assert run.record_count == 10
        assert run.finished_at is not None
        assert run.total_duration_ms is not None
        assert run.total_duration_ms >= 0

    def test_time_stage_records_success(self):
        collector = PipelineMetricsCollector()
        run = collector.start_run("p3", "boost_watch_time")
        with collector.time_stage(run, stage="trend"):
            time.sleep(0.01)
        assert len(run.stages) == 1
        stage = run.stages[0]
        assert stage.stage == "trend"
        assert stage.success is True
        assert stage.duration_ms >= 0

    def test_time_stage_records_failure(self):
        collector = PipelineMetricsCollector()
        run = collector.start_run("p4", "grow_subscribers")
        with pytest.raises(ValueError):
            with collector.time_stage(run, stage="ranking"):
                raise ValueError("simulated error")
        assert run.stages[0].success is False
        assert "simulated error" in run.stages[0].error

    def test_multiple_stages_appended(self):
        collector = PipelineMetricsCollector()
        run = collector.start_run("p5", "increase_ctr")
        with collector.time_stage(run, stage="anomaly"):
            pass
        with collector.time_stage(run, stage="ranking"):
            pass
        assert len(run.stages) == 2
        assert run.stages[0].stage == "anomaly"
        assert run.stages[1].stage == "ranking"

    def test_to_dict_is_serialisable(self):
        collector = PipelineMetricsCollector()
        run = collector.start_run("p6", "boost_watch_time")
        with collector.time_stage(run, stage="trend"):
            pass
        collector.finish_run(run, success=True)
        d = run.to_dict()
        assert isinstance(d, dict)
        assert d["goal"] == "boost_watch_time"
        assert len(d["stages"]) == 1
