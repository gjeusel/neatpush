import asyncio
import dataclasses
import datetime
from typing import Any, TypedDict

import arq
import edgedb
import structlog

from . import clients
from .config import CFG

log = structlog.get_logger()


class ARQBaseContext(TypedDict):
    manga: clients.MangaClient
    edb: edgedb.AsyncIOClient


class ARQContext(ARQBaseContext):
    enqueue_time: datetime.datetime
    job_id: str
    job_try: int
    score: float
    redis: arq.ArqRedis


async def fetch_manga_chapters(ctx: ARQContext, name: str):
    chapters = await ctx["manga"].get_neatmanga_latest_releases(name)

    # Upsert results
    upsert_chapter_qry = """
        INSERT MangaChapter {
            num := <str>$num,
            timestamp := <datetime>$timestamp,
            url := <str>$url,
            manga := (SELECT Manga FILTER .name = <str>$name)
        }
        UNLESS CONFLICT ON .url
    """
    for chapter in chapters:
        await ctx["edb"].query(
            upsert_chapter_qry, **dataclasses.asdict(chapter), name=name
        )

    # Check if need to notify
    to_notify_qry = """
        SELECT MangaChapter { num, url }
        FILTER .notif_status.notified = false AND .manga.name = <str>$name
    """
    chapters = await ctx["edb"].query(to_notify_qry, name=name)
    for chapter in chapters:
        log.info("chapter-to-notify", num=chapter.num, name=name)


async def manga_fetch_job(ctx: ARQContext) -> None:
    mangas = await ctx["edb"].query("SELECT Manga { name }")

    coroutines = [
        ctx["redis"].enqueue_job(fetch_manga_chapters.__name__, name=manga.name)
        for manga in mangas
    ]
    await asyncio.gather(*coroutines)


WORKER_FUNCTIONS = [manga_fetch_job, fetch_manga_chapters]
CRON_JOBS = [arq.cron(manga_fetch_job, minute=None, run_at_startup=True)]


def generate_worker_settings() -> dict[str, Any]:
    loop = asyncio.get_event_loop()

    redis_settings = arq.connections.RedisSettings.from_dsn(str(CFG.REDIS_DSN))
    redis_settings.conn_timeout = CFG.REDIS_TIMEOUT
    redis_pool = loop.run_until_complete(arq.create_pool(redis_settings))
    redis_pool.connection_pool.max_connections = CFG.REDIS_MAXCONN

    async def on_startup(ctx: dict[str, Any]) -> None:
        log.info("arq-worker-start", dsn=str(CFG.REDIS_DSN))

    async def on_shutdown(ctx: dict[str, Any]) -> None:
        log.debug("arq-worker-stop")

    async def on_job_start(ctx: ARQContext) -> None:
        log.debug("arq-job-start", job_try=ctx["job_try"], job_id=ctx["job_id"])

    async def on_job_end(ctx: ARQContext) -> None:
        log.debug("arq-job-end", job_try=ctx["job_try"], job_id=ctx["job_id"])

    ctx: ARQBaseContext = {
        "manga": clients.MangaClient(),
        "edb": edgedb.create_async_client(dsn=CFG.EDGEDB_DSN),
    }

    settings = dict(
        ctx=ctx,
        redis_pool=redis_pool,
        functions=WORKER_FUNCTIONS,
        cron_jobs=CRON_JOBS,
        #
        on_startup=on_startup,
        on_shutdown=on_shutdown,
        on_job_start=on_job_start,
        on_job_end=on_job_end,
        #
        max_jobs=CFG.ARQ_MAX_JOBS,
        job_timeout=CFG.ARQ_JOB_TIMEOUT,
        keep_result=CFG.ARQ_KEEP_RESULT,
        max_tries=CFG.ARQ_MAX_TRIES,
        health_check_interval=CFG.ARQ_HEALTH_CHECK_INTERVAL,
    )

    return settings
