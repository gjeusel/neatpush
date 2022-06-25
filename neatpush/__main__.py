import asyncio

import arq
import edgedb
import typer
import uvloop
from arq.cli import watch_reload as run_worker_watch_reload

from .config import CFG
from .constant import SRC_DIR
from .tasks import generate_worker_settings

uvloop.install()

loop = asyncio.get_event_loop()

cli = typer.Typer()

db = edgedb.create_client(CFG.EDGEDB_DSN)


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


@cli.command("seed")
def seed():
    # Cleanup
    for t in ("MangaChapter", "NotifStatus", "Manga"):
        db.query(f"DELETE {t}")

    # Generate data
    mangas = ("berserk", "overgeared-2020")
    for manga in mangas:
        db.query("INSERT Manga { name := <str>$name }", name=manga)


if __name__ == "__main__":
    cli()
