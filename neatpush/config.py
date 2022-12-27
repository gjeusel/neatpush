import logging
import sys
from pathlib import Path

import pydantic
import structlog
from pydantic.types import SecretStr

PKG_DIR = Path(__file__).parents[1]


class Config(pydantic.BaseSettings):
    # AWS:
    AWS_ACCESS_KEY: str = ""
    AWS_SECRET_KEY: SecretStr = SecretStr("")
    AWS_REGION_NAME: str = "eu-west-3"
    AWS_SNS_TOPIC: str = ""

    # Scaleway
    # limitation: can't start with "SCW" (https://www.scaleway.com/en/docs/compute/containers/reference-content/containers-limitations/)
    MY_SCW_ACCESS_KEY: str = ""
    MY_SCW_SECRET_KEY: SecretStr = SecretStr("")
    MY_SCW_REGION_NAME: str = "fr-par"
    MY_SCW_BUCKET_ENDPOINT_URL: str = ""
    MY_SCW_BUCKET: str = "messy"

    # SMS
    SEND_SMS: bool = False
    SMS_MAX_LEN: int = 200

    NEATMANGA: list[str] = pydantic.Field(default_factory=list)
    MANGAPILL: list[str] = pydantic.Field(default_factory=list)
    TOONILY: list[str] = pydantic.Field(default_factory=list)

    class Config:
        env_file = (PKG_DIR / ".env").as_posix()


CFG = Config()


def setup_logging(level: str = "info") -> None:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso", utc=False),
            structlog.dev.ConsoleRenderer(sort_keys=False, colors=sys.stderr.isatty()),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper())
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )
