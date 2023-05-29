import logging
import sys
from pathlib import Path

import apprise
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

    # Simple Push
    SIMPLE_PUSH_KEY: SecretStr = SecretStr("")

    NEATMANGA: list[str] = pydantic.Field(default_factory=list)
    MANGAPILL: list[str] = pydantic.Field(default_factory=list)
    TOONILY: list[str] = pydantic.Field(default_factory=list)

    _notif_manager: apprise.Apprise = pydantic.PrivateAttr()

    @property
    def notif_manager(self) -> apprise.Apprise:
        if not hasattr(self, "_notif_manager"):
            manager = apprise.Apprise()

            has_aws_creds = all(
                [
                    self.AWS_ACCESS_KEY,
                    self.AWS_SECRET_KEY,
                    self.AWS_REGION_NAME,
                    self.AWS_SNS_TOPIC,
                ]
            )
            if self.SEND_SMS and has_aws_creds:
                sns = "sns://{access_key}/{secret_key}/{region}/{topic}".format(
                    access_key=self.AWS_ACCESS_KEY,
                    secret_key=self.AWS_SECRET_KEY.get_secret_value(),
                    region=self.AWS_REGION_NAME,
                    topic=self.AWS_SNS_TOPIC,
                )
                manager.add(sns, tag="sms")

            if self.SIMPLE_PUSH_KEY:
                manager.add(
                    f"spush://{self.SIMPLE_PUSH_KEY.get_secret_value()}",
                    tag="always",
                )

            self._notif_manager = manager

        return self._notif_manager

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

    for _logger_name in ["uvicorn", "uvicorn.error"]:
        # Clear the log handlers for uvicorn loggers, and enable propagation
        # so the messages are caught by our root logger and formatted correctly
        # by structlog
        _logger = logging.getLogger(_logger_name)
        _logger.handlers.clear()
        _logger.propagate = True
