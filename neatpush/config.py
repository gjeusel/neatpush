import logging
from pathlib import Path

import pydantic
import structlog

ENV_FILE_PATH = Path(__file__).parents[1] / ".env"


class Config(pydantic.BaseSettings):
    # Twilio API
    # https://console.twilio.com/us1/develop/sms/settings/whatsapp-sandbox?frameUrl=%2Fconsole%2Fsms%2Fwhatsapp%2Fsandbox%3Fx-target-region%3Dus1  # noqa
    TWILIO_ENABLED: bool = False
    TWILIO_ACCOUNT_SID: str | None = None
    TWILIO_SERVICE_SID: str | None = None
    TWILIO_AUTH_TOKEN: str | None = None
    TWILIO_NUM_FROM: str | None = None
    TWILIO_NUM_TO: str | None = None

    # EDGEDB:
    EDGEDB_DSN: str | None = None  # "edgedb://edgedb@localhost:10703/neatpush"
    EDGEDB_TLS_SECURITY: str | None = None  # "insecure"

    # Redis cfg:
    REDIS_DSN: pydantic.RedisDsn = "redis://localhost:6379"  # pyright: ignore
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
