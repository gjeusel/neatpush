import asyncio
from typing import Any

import arq
import typer
import uvloop
from arq.cli import watch_reload as run_worker_watch_reload

import prisma

from . import clients
from .config import CFG
from .constant import SRC_DIR
from .tasks import create_arq_redis, generate_worker_settings

uvloop.install()

loop = asyncio.get_event_loop()


cli = typer.Typer()


@cli.command("worker")
def run_worker(
    burst: bool = typer.Option(False, "--burst/--no-burst"),
    watch: bool = typer.Option(True, "--watch/--no-watch"),
):
    kwargs: dict[str, Any] = {"burst": burst}
    worker_settings = generate_worker_settings()

    if watch:
        kwargs["watch"] = SRC_DIR.as_posix()
        loop.run_until_complete(
            run_worker_watch_reload(
                path=SRC_DIR.as_posix(), worker_settings=worker_settings
            )
        )
    else:
        arq.run_worker(worker_settings, **kwargs)


task_cli = typer.Typer()
cli.add_typer(task_cli, name="task")


@task_cli.command("enqueue")
def task_enqueue(name: str):
    redis = create_arq_redis()
    loop.run_until_complete(redis.enqueue_job(name))


db_cli = typer.Typer()
cli.add_typer(db_cli, name="db")


@db_cli.command("seed")
def seed():
    async def _seed():
        db = prisma.Prisma()
        await db.connect()

        # Cleanup
        for t in (db.mangachapter, db.manga):
            await t.delete_many()

        # Generate data
        mangas = (
            "one-piece",
            "one-punch-man",
            "berserk",
            "omniscient-readers-viewpoint",
            "overgeared-2020",
            "tales-of-demons-and-gods",
        )
        await db.manga.create_many(data=[{"name": name} for name in mangas])

    loop.run_until_complete(_seed())


@cli.command("msg")
def send_message(message: str = "Hello"):
    if not all(
        (
            CFG.TWILIO_ACCOUNT_SID,
            CFG.TWILIO_SERVICE_SID,
            CFG.TWILIO_AUTH_TOKEN,
            CFG.TWILIO_NUM_TO,
            CFG.TWILIO_NUM_FROM,
        )
    ):
        raise RuntimeError("Missing configuration for TWILIO.")

    client = clients.TwilioClient(
        account_sid=str(CFG.TWILIO_ACCOUNT_SID),
        service_sid=str(CFG.TWILIO_SERVICE_SID),
        auth_token=str(CFG.TWILIO_AUTH_TOKEN),
    )
    loop.run_until_complete(
        client.send_whatsapp_msg(
            num_to=str(CFG.TWILIO_NUM_TO), num_from=CFG.TWILIO_NUM_FROM, message=message
        )
    )


if __name__ == "__main__":
    cli()
