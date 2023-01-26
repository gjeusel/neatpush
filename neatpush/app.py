import logging

import structlog
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route

from neatpush.config import CFG, setup_logging

from . import manga, notify

# Handle uvicorn loggings:
# - forward uvicorn error logs into structlog
# - silence uvicorn access logs

for _logger_name in ["uvicorn", "uvicorn.error"]:
    # Clear the log handlers for uvicorn loggers, and enable propagation
    # so the messages are caught by our root logger and formatted correctly
    # by structlog
    _logger = logging.getLogger(_logger_name)
    _logger.handlers.clear()
    _logger.propagate = True

logger = structlog.getLogger(__name__)


async def homepage(request: Request) -> PlainTextResponse:
    map_new_chapters = manga.get_new_chapters()
    message = notify.format_new_chapters(map_new_chapters)

    if message:
        if len(message) < CFG.SMS_MAX_LEN:
            if CFG.SEND_SMS:
                notify.send_sms(message)
        else:
            logger.warn(f"Message is too long, not sending SMS:\n{message}")

    return PlainTextResponse(message)


routes = [Route("/", endpoint=homepage, methods=["POST", "GET"])]

app = Starlette(debug=True, routes=routes)


@app.on_event("startup")
def _setup_logs_for_app() -> None:
    setup_logging()
