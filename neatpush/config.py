import logging
from pathlib import Path

import pydantic
import structlog

PKG_DIR = Path(__file__).parents[1]


class Config(pydantic.BaseSettings):
    class Config:
        env_file = (PKG_DIR / ".env").as_posix()


CFG = Config()


structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso", utc=False),
        structlog.dev.ConsoleRenderer(sort_keys=False),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.NOTSET),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)
