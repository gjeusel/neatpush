import logging
from pathlib import Path

import pydantic
import structlog

ENV_FILE_PATH = Path(__file__).parents[1] / ".env"


class Config(pydantic.BaseSettings):
    # EDGEDB:
    EDGEDB_DSN: str | None = None  #  "edgedb://edgedb@localhost:10703/neatpush"

    # Redis cfg:
    REDIS_DSN: pydantic.RedisDsn = "redis://localhost:6379"
    REDIS_TIMEOUT: int = 60
    # REDIS_MINCONN: int = 1
    REDIS_MAXCONN: int = 10

    # Arq config:
    ARQ_MAX_JOBS: int = 10
    ARQ_JOB_TIMEOUT: int = 60  # seconds
    ARQ_KEEP_RESULT: int = 60  # seconds
    ARQ_MAX_TRIES: int = 5
    ARQ_HEALTH_CHECK_INTERVAL: int = 60  # seconds

    class Config:
        env_file = ENV_FILE_PATH.as_posix()


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
