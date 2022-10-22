import asyncio
import datetime
import uuid
from itertools import chain
from typing import Any, TypedDict

import arq
import edgedb
import structlog

from . import clients, queries
from .config import CFG

log = structlog.get_logger()


class ARQBaseContext(TypedDict):
    manga: clients.MangaClient
    edb: edgedb.AsyncIOClient
    twilio: clients.TwilioClient


class ARQContext(ARQBaseContext):
    enqueue_time: datetime.datetime
    job_id: str
    job_try: int
    score: float
    redis: arq.ArqRedis


async def fetch_manga_chapters(ctx: ARQContext, name: str) -> list[uuid.UUID]:
    chapters = await ctx["manga"].get_neatmanga_latest_releases(name)

    promises = [
        queries.upsert_chapter(
            client=ctx["edb"],
            num=chap.num,
            timestamp=chap.timestamp,
            url=chap.url,
            manga_name=name,
        )
        for chap in chapters
    ]
    new_chapters = await asyncio.gather(*promises)
    if new_chapters:
        log.info("new-chapter", manga=name, number=len(new_chapters))

    return [obj.id for obj in new_chapters]


async def notify_manga_chapters(ctx: ARQContext) -> None:
    to_notify_qry = """
        SELECT MangaChapter { id, name := .manga.name, num, url }
        filter .notified = false
    """
    chapters = await ctx["edb"].query(to_notify_qry)

    for chapter in chapters:
        log.info("notify", manga=chapter.name, num=chapter.num, url=chapter.url)
        if CFG.TWILIO_ENABLED:
            message = f"*{chapter.name}* - New Chapter {chapter.num} !\n{chapter.url}"
            await ctx["twilio"].send_whatsapp_msg(
                message=message,
                num_from=str(CFG.TWILIO_NUM_FROM),
                num_to=str(CFG.TWILIO_NUM_TO),
            )

    notified_qry = """
        UPDATE MangaChapter
        FILTER .id in array_unpack(<array<uuid>>$uuids)
        SET {notified := true}
    """
    await ctx["edb"].query(notified_qry, uuids=[chapter.id for chapter in chapters])

    log.info("")


async def manga_job(ctx: ARQContext) -> None:
    mangas = await ctx["edb"].query("SELECT Manga { name }")

    fetch_coroutines = [
        ctx["redis"].enqueue_job(fetch_manga_chapters.__name__, name=manga.name)
        for manga in mangas
    ]
    ops = await asyncio.gather(*fetch_coroutines)

    new_chapters = await asyncio.gather(
        *[op.result(timeout=CFG.REDIS_TIMEOUT) for op in ops]
    )
    uuid_chapters = list(chain.from_iterable(new_chapters))

    if uuid_chapters:
        log.info("new-chapters", number=len(uuid_chapters))
        await ctx["redis"].enqueue_job(notify_manga_chapters.__name__)


WORKER_FUNCTIONS = [manga_job, fetch_manga_chapters, notify_manga_chapters]

every_5_min = tuple(range(0, 60, 5))  # "*/5" not working in arq

CRON_JOBS = [
    arq.cron(manga_job, minute=every_5_min),  # type: ignore
    # arq.cron(notify_manga_chapters, minute=every_5_min),
]


def create_arq_redis() -> arq.ArqRedis:
    loop = asyncio.get_event_loop()
    redis_settings = arq.connections.RedisSettings.from_dsn(str(CFG.REDIS_DSN))
    redis_settings.conn_timeout = CFG.REDIS_TIMEOUT
    redis_pool = loop.run_until_complete(arq.create_pool(redis_settings))
    redis_pool.connection_pool.max_connections = CFG.REDIS_MAXCONN
    return redis_pool


def generate_worker_settings() -> dict[str, Any]:
    redis_pool = create_arq_redis()

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
        "edb": edgedb.create_async_client(
            dsn=CFG.EDGEDB_DSN, tls_security=CFG.EDGEDB_TLS_SECURITY
        ),
        "twilio": clients.TwilioClient(
            account_sid=str(CFG.TWILIO_ACCOUNT_SID),
            auth_token=str(CFG.TWILIO_AUTH_TOKEN),
        ),
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
