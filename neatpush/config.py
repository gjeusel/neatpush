import logging
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
    SCW_ACCESS_KEY: str = ""
    SCW_SECRET_KEY: SecretStr = SecretStr("")
    SCW_REGION_NAME: str = "fr-par"
    SCW_BUCKET_ENDPOINT_URL: str = ""
    SCW_BUCKET: str = "messy"

    # SMS
    SEND_SMS: bool = False

    NEATMANGA: list[str] = pydantic.Field(default_factory=list)
    MANGAPILL: list[str] = pydantic.Field(default_factory=list)
    TOONILY: list[str] = pydantic.Field(default_factory=list)

    class Config:
        env_file = (PKG_DIR / ".env").as_posix()


CFG = Config()


def setup_logging() -> None:
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
