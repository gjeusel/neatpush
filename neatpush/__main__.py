import asyncio

import arq
import edgedb
import typer
import uvloop
from arq.cli import watch_reload as run_worker_watch_reload

from . import clients
from .config import CFG
from .constant import SRC_DIR
from .tasks import create_arq_redis, generate_worker_settings

uvloop.install()

loop = asyncio.get_event_loop()

cli = typer.Typer()

db = edgedb.create_client(dsn=CFG.EDGEDB_DSN, tls_security=CFG.EDGEDB_TLS_SECURITY)


@cli.command("worker")
def run_worker(
    burst: bool = typer.Option(False, "--burst/--no-burst"),
    watch: bool = typer.Option(True, "--watch/--no-watch"),
):
    kwargs = {"burst": burst}
    worker_settings = generate_worker_settings()

    if watch:
        kwargs["watch"] = SRC_DIR.as_posix()
        loop.run_until_complete(
            run_worker_watch_reload(
                path=SRC_DIR.as_posix(), worker_settings=worker_settings
            )
        )
    else:
        loop.run_until_complete(arq.run_worker(worker_settings, **kwargs))


@cli.command("ping")
def ping():
    worker_settings = generate_worker_settings()
    arq.worker.check_health(worker_settings)


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
    # Cleanup
    for t in ("MangaChapter", "Manga"):
        db.query(f"DELETE {t}")

    # Generate data
    mangas = (
        "one-piece",
        "one-punch-man",
        "berserk",
        "omniscient-readers-viewpoint",
        "overgeared-2020",
        "tales-of-demons-and-gods",
    )
    for manga in mangas:
        db.query("INSERT Manga { name := <str>$name }", name=manga)


@cli.command("msg")
def send_message(message: str = "Hello"):
    client = clients.TwilioClient(
        account_sid=CFG.TWILIO_ACCOUNT_SID,
        service_sid=CFG.TWILIO_SERVICE_SID,
        auth_token=CFG.TWILIO_AUTH_TOKEN,
    )
    loop.run_until_complete(
        client.send_whatsapp_msg(
            num_to=CFG.TWILIO_NUM_TO, num_from=CFG.TWILIO_NUM_FROM, message=message
        )
    )


if __name__ == "__main__":
    cli()
