import asyncio
import dataclasses
import datetime
import uuid

# from itertools import chain
from typing import Any, Awaitable, TypedDict

import arq

# import orjson
import structlog

import prisma

from . import clients
from .config import CFG

log = structlog.get_logger()


class ARQBaseContext(TypedDict):
    manga: clients.MangaClient
    db: prisma.Prisma
    twilio: clients.TwilioClient | None
    redis: arq.ArqRedis


class ARQContext(ARQBaseContext):
    enqueue_time: datetime.datetime
    job_id: str
    job_try: int
    score: float
    redis: arq.ArqRedis


async def fetch_manga_chapters(ctx: ARQContext, name: str) -> list[uuid.UUID]:
    db = ctx["db"]

    chapters = await ctx["manga"].get_neatmanga_latest_releases(name)
    coroutines: list[Awaitable[Any]] = []
    for chapter in chapters:
        coroutines.append(
            db.mangachapter.upsert(
                where={"url": chapter.url},
                data={
                    "create": dataclasses.asdict(chapter),
                },
            )
        )

    results = await asyncio.gather(*coroutines)
    __import__("pdb").set_trace()  # BREAKPOINT

    # new_chapters = await queries.manga_chapters_upsert(
    #     ctx["db"], chapters=orjson.dumps(chapters).decode("utf-8"), name=name
    # )
    # if new_chapters:
    #     log.info("new-chapter", manga=name, number=len(new_chapters))

    # return [obj.id for obj in new_chapters]


async def notify_manga_chapters(ctx: ARQContext) -> None:
    # to_notify_qry = """
    #     SELECT MangaChapter { id, name := .manga.name, num, url }
    #     filter .notified = false
    # """
    # chapters = await ctx["edb"].query(to_notify_qry)

    chapters = await ctx["db"].mangachapter.find_many(
        where={"notified": False},
        include={"manga": {"select": {"name": True}}},
    )
    __import__("pdb").set_trace()  # BREAKPOINT

    # for chapter in chapters:
    #     log.info("notify", manga=chapter.name, num=chapter.num, url=chapter.url)
    #     if CFG.TWILIO_ENABLED:
    #         message = f"*{chapter.name}* - New Chapter {chapter.num} !\n{chapter.url}"
    #         await ctx["twilio"].send_whatsapp_msg(
    #             message=message, num_from=CFG.TWILIO_NUM_FROM, num_to=CFG.TWILIO_NUM_TO
    #         )

    # notified_qry = """
    #     UPDATE MangaChapter
    #     FILTER .id in array_unpack(<array<uuid>>$uuids)
    #     SET {notified := true}
    # """
    # await ctx["edb"].query(notified_qry, uuids=[chapter.id for chapter in chapters])


async def manga_job(ctx: ARQContext) -> None:
    mangas = await ctx["db"].manga.find_many(
    )
    __import__("pdb").set_trace()  # BREAKPOINT

    # fetch_coroutines = [
    #     ctx["redis"].enqueue_job(fetch_manga_chapters.__name__, name=manga.name)
    #     for manga in mangas
    # ]
    # ops = await asyncio.gather(*fetch_coroutines)

    # new_chapters = await asyncio.gather(
    #     *[op.result(timeout=CFG.REDIS_TIMEOUT) for op in ops]
    # )
    # uuid_chapters = list(chain.from_iterable(new_chapters))

    # if uuid_chapters:
    #     log.info("new-chapters", number=len(uuid_chapters))
    #     ctx["redis"].enqueue_job(notify_manga_chapters.__name__)


WORKER_FUNCTIONS = [manga_job, fetch_manga_chapters, notify_manga_chapters]

every_5_min = tuple(range(0, 60, 5))  # "*/5" not working in arq

CRON_JOBS = [
    arq.cron(manga_job, minute=every_5_min, run_at_startup=True),
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

    if not all((CFG.TWILIO_ENABLED, CFG.TWILIO_ACCOUNT_SID, CFG.TWILIO_AUTH_TOKEN)):
        twilio = None
    else:
        twilio = clients.TwilioClient(
            account_sid=str(CFG.TWILIO_ACCOUNT_SID),
            auth_token=str(CFG.TWILIO_AUTH_TOKEN),
        )

    ctx: ARQBaseContext = {
        "manga": clients.MangaClient(),
        "db": prisma.Prisma(),
        "twilio": twilio,
        "redis": redis_pool,
    }

    async def on_startup(ctx: ARQBaseContext) -> None:
        await ctx["db"].connect()
        log.info("arq-worker-start", dsn=str(CFG.REDIS_DSN))

    async def on_shutdown(ctx: ARQBaseContext) -> None:
        await ctx["db"].disconnect()
        log.debug("arq-worker-stop")

    async def on_job_start(ctx: ARQContext) -> None:
        log.debug("arq-job-start", job_try=ctx["job_try"], job_id=ctx["job_id"])

    async def on_job_end(ctx: ARQContext) -> None:
        log.debug("arq-job-end", job_try=ctx["job_try"], job_id=ctx["job_id"])

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
