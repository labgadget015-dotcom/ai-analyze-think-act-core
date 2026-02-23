"""
Structured Logging & Pipeline Metrics.
Provides JSON-formatted log records and a lightweight metrics collector for
monitoring analysis pipeline health, latency, and LLM usage.
"""

import json
import logging
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# JSON log formatter
# ---------------------------------------------------------------------------

class JSONFormatter(logging.Formatter):
    """Emit each log record as a single-line JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        log_object: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_object["exception"] = self.formatException(record.exc_info)
        # Merge any extra fields the caller attached
        for key, value in record.__dict__.items():
            if key not in (
                "name", "msg", "args", "levelname", "levelno", "pathname",
                "filename", "module", "exc_info", "exc_text", "stack_info",
                "lineno", "funcName", "created", "msecs", "relativeCreated",
                "thread", "threadName", "processName", "process", "message",
            ):
                log_object[key] = value
        return json.dumps(log_object, default=str)


def get_json_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Return a logger that emits JSON to stdout."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
    return logger


# ---------------------------------------------------------------------------
# Pipeline metrics
# ---------------------------------------------------------------------------

@dataclass
class StageMetric:
    """Timing and outcome for one pipeline stage."""
    stage: str
    goal: str
    started_at: str
    duration_ms: float
    success: bool
    error: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineRunMetric:
    """Aggregated metrics for a complete pipeline run."""
    pipeline_id: str
    goal: str
    started_at: str
    stages: List[StageMetric] = field(default_factory=list)
    finished_at: Optional[str] = None
    total_duration_ms: Optional[float] = None
    success: Optional[bool] = None
    record_count: int = 0
    token_summary: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        return result


class PipelineMetricsCollector:
    """
    Lightweight metrics collector for pipeline runs.

    Usage::

        collector = PipelineMetricsCollector()
        run = collector.start_run(pipeline_id="run_001", goal="grow_subscribers")

        with collector.time_stage(run, stage="trend"):
            # ... do work ...
            pass

        collector.finish_run(run, success=True, record_count=42)
        print(run.to_dict())
    """

    def __init__(self):
        self._logger = get_json_logger(__name__)

    def start_run(self, pipeline_id: str, goal: str) -> PipelineRunMetric:
        run = PipelineRunMetric(
            pipeline_id=pipeline_id,
            goal=goal,
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        self._logger.info(
            "Pipeline run started",
            extra={"pipeline_id": pipeline_id, "goal": goal},
        )
        return run

    def time_stage(self, run: PipelineRunMetric, stage: str):
        """Context manager that records duration and outcome for one stage."""
        return _StageTimer(run=run, stage=stage, collector=self)

    def finish_run(
        self,
        run: PipelineRunMetric,
        success: bool,
        record_count: int = 0,
        token_summary: Optional[Dict[str, Any]] = None,
    ) -> None:
        run.finished_at = datetime.now(timezone.utc).isoformat()
        start = datetime.fromisoformat(run.started_at)
        end = datetime.fromisoformat(run.finished_at)
        run.total_duration_ms = (end - start).total_seconds() * 1000
        run.success = success
        run.record_count = record_count
        run.token_summary = token_summary
        self._logger.info(
            "Pipeline run finished",
            extra={
                "pipeline_id": run.pipeline_id,
                "goal": run.goal,
                "success": success,
                "total_duration_ms": run.total_duration_ms,
                "record_count": record_count,
            },
        )

    def _record_stage(
        self,
        run: PipelineRunMetric,
        metric: StageMetric,
    ) -> None:
        run.stages.append(metric)
        level = logging.INFO if metric.success else logging.ERROR
        self._logger.log(
            level,
            "Stage completed",
            extra={
                "pipeline_id": run.pipeline_id,
                "stage": metric.stage,
                "goal": metric.goal,
                "duration_ms": metric.duration_ms,
                "success": metric.success,
                "error": metric.error,
            },
        )


class _StageTimer:
    """Internal context manager used by PipelineMetricsCollector.time_stage."""

    def __init__(
        self,
        run: PipelineRunMetric,
        stage: str,
        collector: "PipelineMetricsCollector",
    ):
        self._run = run
        self._stage = stage
        self._collector = collector
        self._start: float = 0.0

    def __enter__(self):
        self._start = time.monotonic()
        self._started_at = datetime.now(timezone.utc).isoformat()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.monotonic() - self._start) * 1000
        success = exc_type is None
        error = str(exc_val) if exc_val else None
        metric = StageMetric(
            stage=self._stage,
            goal=self._run.goal,
            started_at=self._started_at,
            duration_ms=round(duration_ms, 3),
            success=success,
            error=error,
        )
        self._collector._record_stage(self._run, metric)
        return False  # Do not suppress exceptions


# Module-level convenience instance
metrics = PipelineMetricsCollector()
