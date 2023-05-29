from __future__ import annotations

from typing import Any

import orjson
import structlog
from apprise import NotifyFormat
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from . import manga
from .config import CFG, setup_logging
from .scraping import MangaChapter

logger = structlog.getLogger("neatpush")


class ORJSONReponse(JSONResponse):
    def render(self, content: Any) -> bytes:
        return orjson.dumps(content)


def _format_notif_infos(
    map_new_chapters: dict[str, list[MangaChapter]]
) -> tuple[str, str]:
    total_chapters = 0
    names: list[str] = []
    pieces: list[str] = []
    for name, chapters in map_new_chapters.items():
        if chapters:
            total_chapters += len(chapters)
            names.append(name)

        for chapter in chapters:
            pieces.append(f"- [{name} #{chapter.num}]({chapter.url})")

    title = f"Neatpush ({', '.join(names)})"
    body = "\n".join(pieces)
    return title, body


def check_new_chapters() -> dict[str, list[MangaChapter]]:
    map_new_chapters = manga.get_new_chapters()

    if map_new_chapters:
        logger.info(f"Found new chapters for {', '.join(map_new_chapters.keys())}")

        title, body = _format_notif_infos(map_new_chapters)

        tag = "all" if (CFG.SEND_SMS and len(body) < CFG.SMS_MAX_LEN) else "always"

        CFG.notif_manager.notify(
            title=title,
            body=body,
            tag=tag,
            body_format=NotifyFormat.MARKDOWN,
        )

    return map_new_chapters


async def homepage(request: Request) -> ORJSONReponse:
    map_new_chapters = check_new_chapters()
    return ORJSONReponse(map_new_chapters)


routes = [Route("/", endpoint=homepage, methods=["POST", "GET"])]

app = Starlette(debug=True, routes=routes)


@app.on_event("startup")
def _setup_logs_for_app() -> None:
    setup_logging()
