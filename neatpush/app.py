from __future__ import annotations

from typing import Any

import orjson
import structlog
from apprise import NotifyFormat
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from neatpush import manga
from neatpush.config import CFG, setup_logging
from neatpush.scraping import MangaChapter

logger = structlog.getLogger("neatpush")


class ORJSONReponse(JSONResponse):
    def render(self, content: Any) -> bytes:
        return orjson.dumps(content)


def _format_notif_infos(
    map_new_chapters: dict[str, list[MangaChapter]],
) -> tuple[str, str]:
    total_chapters = 0
    names: list[str] = []
    pieces: list[str] = []
    for name, chapters in map_new_chapters.items():
        if chapters:
            total_chapters += len(chapters)
            names.append(name)

        pieces.extend(
            f"- [{name} #{chapter.num}]({chapter.url})" for chapter in chapters
        )

    title = f"Neatpush ({', '.join(names)})"
    body = "\n".join(pieces)
    return title, body


def check_new_chapters() -> dict[str, list[MangaChapter]]:
    map_new_chapters = manga.get_new_chapters()

    if map_new_chapters:
        logger.info("notifying", **map_new_chapters)
        title, body = _format_notif_infos(map_new_chapters)

        CFG.notif_manager.notify(
            title=title,
            body=body,
            body_format=NotifyFormat.MARKDOWN,
        )

    return map_new_chapters


async def trigger_chapters_check(request: Request) -> ORJSONReponse:
    map_new_chapters = check_new_chapters()
    return ORJSONReponse(map_new_chapters)


async def ping(request: Request) -> Response:
    return Response(content="pong")


routes = [
    Route("/", endpoint=trigger_chapters_check, methods=["POST", "GET"]),
    Route("/ping", endpoint=ping, methods=["GET"]),
]

app = Starlette(debug=True, routes=routes)


@app.on_event("startup")
def _setup_logs_for_app() -> None:
    setup_logging(level=CFG.LOG_LEVEL)
