import json
import logging

from app.core.logging import JsonFormatter


def test_json_formatter_retains_structured_fields_and_safe_exception_information() -> None:
    try:
        raise RuntimeError("secret-bearing detail must not be logged")
    except RuntimeError:
        record = logging.LogRecord(
            name="app.services.worker",
            level=logging.ERROR,
            pathname=__file__,
            lineno=1,
            msg="analysis_worker_stage_failed",
            args=(),
            exc_info=__import__("sys").exc_info(),
        )
    record.analysis_job_id = "analysis-123"
    record.stage_name = "repository_parsing"
    record.exception_type = "RuntimeError"

    payload = json.loads(JsonFormatter().format(record))

    assert payload["analysis_job_id"] == "analysis-123"
    assert payload["stage_name"] == "repository_parsing"
    assert payload["exception_type"] == "RuntimeError"
    assert "Traceback (most recent call last)" in payload["exception"]
    assert "RuntimeError: exception details redacted" in payload["exception"]
    assert "secret-bearing detail" not in payload["exception"]
