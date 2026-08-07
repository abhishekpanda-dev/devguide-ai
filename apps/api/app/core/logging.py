import json
import logging
import traceback
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.core.middleware import correlation_id_context

_RESERVED = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": correlation_id_context.get(),
        }
        payload.update(
            {
                key: value
                for key, value in record.__dict__.items()
                if key not in _RESERVED and key not in {"message", "asctime"}
            }
        )
        if record.exc_info:
            exception_type, _exception, exception_traceback = record.exc_info
            frames = traceback.extract_tb(exception_traceback) if exception_traceback else []
            safe_exception_type = exception_type.__name__ if exception_type else "Exception"
            safe_frames = (
                f'  File "{Path(frame.filename).name}", line {frame.lineno}, in {frame.name}\n'
                for frame in frames
            )
            payload["exception"] = "".join(
                (
                    "Traceback (most recent call last):\n",
                    *safe_frames,
                    f"{safe_exception_type}: exception details redacted",
                )
            )
        return json.dumps(payload, default=str, separators=(",", ":"))


def configure_logging(level: str) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
