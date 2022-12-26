from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route

from neatpush.config import CFG

from . import manga, notify


async def homepage(request: Request) -> PlainTextResponse:
    map_new_chapters = manga.get_new_chapters()
    message = notify.format_new_chapters(map_new_chapters)

    if CFG.SEND_SMS:
        notify.send_sms(message)

    return PlainTextResponse(message)


routes = [Route("/", endpoint=homepage, methods=["POST", "GET"])]

app = Starlette(debug=True, routes=routes)
