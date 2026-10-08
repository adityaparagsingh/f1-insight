"""ETL logging: console + rotating file under backend/logs/etl.log."""
from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.config import ETL_LOG_DIR

_CONFIGURED = False


def get_logger(name: str = "etl") -> logging.Logger:
    global _CONFIGURED
    root = logging.getLogger("etl")
    if not _CONFIGURED:
        root.setLevel(logging.INFO)
        fmt = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        console = logging.StreamHandler(sys.stdout)
        console.setFormatter(fmt)
        root.addHandler(console)

        try:
            Path(ETL_LOG_DIR).mkdir(parents=True, exist_ok=True)
            fileh = RotatingFileHandler(
                Path(ETL_LOG_DIR) / "etl.log", maxBytes=5 * 1024 * 1024, backupCount=3
            )
            fileh.setFormatter(fmt)
            root.addHandler(fileh)
        except OSError:  # pragma: no cover
            pass

        root.propagate = False
        _CONFIGURED = True

    # Child loggers propagate up to the configured ``etl`` logger.
    logger = logging.getLogger(name)
    logger.setLevel(logging.NOTSET)
    return logger
