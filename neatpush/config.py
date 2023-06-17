import logging
import sys
from pathlib import Path

import apprise
import pydantic
import structlog
from pydantic.types import SecretStr

PKG_DIR = Path(__file__).parents[1]

logger = structlog.getLogger()


class Config(pydantic.BaseSettings):
    # Scaleway limitation: env variable can't start with "SCW" (reserved)
    # https://www.scaleway.com/en/docs/compute/containers/reference-content/containers-limitations/
    CLOUD_ACCESS_KEY: str = ""
    CLOUD_SECRET_KEY: SecretStr = SecretStr("")

    CLOUD_REGION_NAME: str = "fr-par"
    BUCKET_ENDPOINT_URL: str = "https://s3.fr-par.scw.cloud"
    BUCKET_NAME: str = "messy"
    BUCKET_KEY: str = "neatpush.json"

    # Simple Push
    SIMPLE_PUSH_KEY: SecretStr = SecretStr("")

    # Push Technulus
    TECHULUS_PUSH_KEY: SecretStr = SecretStr("")

    NEATMANGA: list[str] = pydantic.Field(default_factory=list)
    MANGAPILL: list[str] = pydantic.Field(default_factory=list)
    TOONILY: list[str] = pydantic.Field(default_factory=list)

    _notif_manager: apprise.Apprise = pydantic.PrivateAttr()

    @property
    def notif_manager(self) -> apprise.Apprise:
        if not hasattr(self, "_notif_manager"):
            manager = apprise.Apprise()

            if secret := self.SIMPLE_PUSH_KEY.get_secret_value():
                manager.add(f"spush://{secret}", tag="always")
                logger.info("Simple Push has been set.")

            if secret := self.TECHULUS_PUSH_KEY.get_secret_value():
                manager.add(f"push://{secret}/", tag="always")
                logger.info("Technulus has been set.")

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
