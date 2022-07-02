import asyncio
import datetime
import uuid
from itertools import chain
from typing import Any, TypedDict

import arq
import edgedb
import orjson
import structlog

from . import clients
from .config import CFG
from .edbqueries import queries

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

    new_chapters = await queries.manga_chapters_upsert(
        ctx["edb"], chapters=orjson.dumps(chapters).decode("utf-8"), name=name
    )
    if new_chapters:
        log.info("new-chapter", manga=name, number=len(new_chapters))

    return [obj.id for obj in new_chapters]


async def notify_manga_chapters(
    ctx: ARQContext, uuid_chapters: list[uuid.UUID]
) -> None:
    chapters_qry = """
        SELECT MangaChapter { name := .manga.name, num, url }
        filter .id in array_unpack(<array<uuid>>$uuids)
    """
    chapters = await ctx["edb"].query(chapters_qry, uuids=uuid_chapters)

    for chapter in chapters:
        log.info("notify", manga=chapter.name, num=chapter.num, url=chapter.url)
        if CFG.TWILIO_ENABLED:
            message = f"*{chapter.name}* - New Chapter {chapter.num} !\n{chapter.url}"
            await ctx["twilio"].send_whatsapp_msg(
                message=message, num_from=CFG.TWILIO_NUM_FROM, num_to=CFG.TWILIO_NUM_TO
            )

    notified_qry = """
        UPDATE NotifStatus
        FILTER .chapters.id in array_unpack(<array<uuid>>$uuids)
        SET {notified := true}
    """
    await ctx["edb"].query(notified_qry, uuids=uuid_chapters)


async def manga_job(ctx: ARQContext) -> None:
    mangas = await ctx["edb"].query("SELECT Manga { name }")

    fetch_coroutines = [
        ctx["redis"].enqueue_job(fetch_manga_chapters.__name__, name=manga.name)
        for manga in mangas
    ]
    ops = await asyncio.gather(*fetch_coroutines)

    new_chapters = await asyncio.gather(*[op.result(timeout=5) for op in ops])
    uuid_chapters = list(chain.from_iterable(new_chapters))

    if uuid_chapters:
        await ctx["redis"].enqueue_job(
            notify_manga_chapters.__name__, uuid_chapters=uuid_chapters
        )


WORKER_FUNCTIONS = [manga_job, fetch_manga_chapters, notify_manga_chapters]
CRON_JOBS = [arq.cron(manga_job, minute=None, run_at_startup=True)]


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
        "twilio": clients.TwilioClient(
            account_sid=CFG.TWILIO_ACCOUNT_SID, auth_token=CFG.TWILIO_AUTH_TOKEN
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
