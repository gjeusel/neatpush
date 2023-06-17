from typing import Any, Optional

import structlog
import typer
import uvicorn
from uvicorn.config import LOGGING_CONFIG

from .app import check_new_chapters
from .manga import _get_s3_client, retrieve_cached_mangas, save_cached_mangas

logger = structlog.getLogger("neatpush")

cli = typer.Typer()


@cli.command("serve")
def run_server(
    port: int = typer.Option(8000, help="port to use"),
    host: str = typer.Option("127.0.0.1", help="host to use"),
    watch: Optional[bool] = typer.Option(None, "--watch/--no-watch"),
) -> None:

    log_config = LOGGING_CONFIG | {
        "loggers": {
            "uvicorn": {"handlers": ["default"], "level": "INFO", "propagate": False},
            "uvicorn.error": {"level": "WARNING"},
            "uvicorn.access": {
                "handlers": ["access"],
                "level": "INFO",
                "propagate": False,
            },
        },
    }

    kwargs: dict[str, Any] = {
        "port": port,
        "host": host,
        "app": "neatpush.app:app",
        "reload": watch,
        "log_config": log_config,
    }
    uvicorn.run(**kwargs)


@cli.command("run")
def run() -> None:
    check_new_chapters()


@cli.command("rmcache")
def rmcache() -> None:
    s3 = _get_s3_client()
    save_cached_mangas(s3, mangas=[])
    logger.info("Removed cached manga")


@cli.command("poplast")
def poplast(name: str = typer.Option(default="omniscient-reader")) -> None:
    s3 = _get_s3_client()
    mangas = retrieve_cached_mangas(s3)

    chapter = None
    for manga in mangas:
        if manga.name == name:
            chapter = manga.chapters.pop(-1)
            break

    if chapter:
        save_cached_mangas(s3, mangas=mangas)
        logger.info(f"Pop last '{name}' chapter ({chapter})")


if __name__ == "__main__":
    cli()
