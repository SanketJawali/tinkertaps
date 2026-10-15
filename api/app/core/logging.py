import json
import logging
import logging.config
from datetime import UTC, datetime

from app.core.config import settings


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_record = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "line": record.lineno,
            "message": record.getMessage(),
        }
        for field in (
            "request_id",
            "job_id",
            "method",
            "path",
            "status_code",
            "duration_ms",
        ):
            value = getattr(record, field, None)
            if value is not None:
                log_record[field] = value

        value = getattr(record, field, None)

        if value is not None:
            log_record[field] = value

            if record.exc_info:
                log_record["exception"] = self.formatException(record.exc_info)

            return json.dumps(log_record)


def setup_logging() -> None:
    if settings.is_production:
        logging.config.dictConfig(
            {
                "version": 1,
                "disable_existing_loggers": False,
                "formatters": {
                    "json": {
                        "()": JsonFormatter,
                    }
                },
                "handlers": {
                    "console": {
                        "class": "logging.StreamHandler",
                        "level": settings.log_level,
                        "formatter": "json",
                        "stream": "ext://sys.stdout",
                    },
                },
                "root": {
                    "handlers": ["console"],
                    "level": settings.log_level,
                },
            }
        )
        return

    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
