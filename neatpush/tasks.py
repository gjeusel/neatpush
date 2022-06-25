import asyncio
import dataclasses
from typing import Any, TypedDict

import aioredis
import arq
import edgedb
import structlog

from . import clients
from .config import CFG

log = structlog.get_logger()


class ARQContext(TypedDict):
    manga: clients.MangaClient
    db: edgedb.AsyncIOClient


async def check_manga(ctx: ARQContext) -> None:
    client = ctx["manga"]
    db = ctx["db"]

    mangas = await db.query("SELECT Manga { name }")
    coroutines = [client.get_neatmanga_latest_releases(manga.name) for manga in mangas]
    results = await asyncio.gather(*coroutines)

    upsert_chapter_qry = """
        INSERT MangaChapter {
            num := <str>$num,
            timestamp := <datetime>$timestamp,
            url := <str>$url,
            manga := (SELECT Manga FILTER .name = <str>$name)
        }
        UNLESS CONFLICT ON .url
    """

    for manga, chapters in zip(mangas, results):
        log.msg(
            "manga-latest-release",
            last=chapters[0].num,
            nchapters=len(chapters),
            name=manga.name,
        )
        for chapter in chapters:
            await db.query(
                upsert_chapter_qry, **dataclasses.asdict(chapter), name=manga.name
            )


WORKER_FUNCTIONS = [check_manga]
CRON_JOBS = [arq.cron(check_manga, minute=None, run_at_startup=True)]


def generate_worker_settings() -> dict[str, Any]:
    loop = asyncio.get_event_loop()
    pool = loop.run_until_complete(
        aioredis.create_pool(
            str(CFG.REDIS_DSN),
            minsize=CFG.REDIS_MINCONN,
            maxsize=CFG.REDIS_MAXCONN,
            create_connection_timeout=CFG.REDIS_TIMEOUT,
            encoding="utf-8",  # needed by arq (string operation on key)
        )
    )

    async def on_startup(ctx: dict[str, Any]) -> None:
        log.msg("arq-worker-start", dsn=str(CFG.REDIS_DSN))

    async def on_shutdown(ctx: dict[str, Any]) -> None:
        log.msg("arq-worker-stop")

    ctx: ARQContext = {
        "manga": clients.MangaClient(),
        "db": edgedb.create_async_client(dsn=CFG.EDGEDB_DSN),
    }

    settings = dict(
        ctx=ctx,
        redis_pool=arq.ArqRedis(pool),
        functions=WORKER_FUNCTIONS,
        cron_jobs=CRON_JOBS,
        #
        on_startup=on_startup,
        on_shutdown=on_shutdown,
        #
        max_jobs=CFG.ARQ_MAX_JOBS,
        job_timeout=CFG.ARQ_JOB_TIMEOUT,
        keep_result=CFG.ARQ_KEEP_RESULT,
        max_tries=CFG.ARQ_MAX_TRIES,
        health_check_interval=CFG.ARQ_HEALTH_CHECK_INTERVAL,
    )

    return settings
