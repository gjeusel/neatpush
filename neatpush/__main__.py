import structlog
import typer
import uvicorn
from uvicorn.config import LOGGING_CONFIG

from .app import check_new_chapters
from .manga import _get_s3_bucket, retrieve_cached_mangas, save_cached_mangas

logger = structlog.getLogger("neatpush")

cli = typer.Typer()


@cli.command("serve")
def run_server(
    port: int = typer.Option(8000, help="port to use"),
    host: str = typer.Option("127.0.0.1", help="host to use"),
    watch: bool = typer.Option(False, "--watch/--no-watch"),
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

    uvicorn.run(
        app="neatpush.app:app",
        port=port,
        host=host,
        reload=watch,
        log_config=log_config,
    )


@cli.command("run")
def run() -> None:
    check_new_chapters()


@cli.command("rmcache")
def rmcache() -> None:
    bucket = _get_s3_bucket()
    save_cached_mangas(bucket, mangas=[])
    logger.info("Removed cached manga")


@cli.command("poplast")
def poplast(name: str = typer.Option(default="omniscient-reader")) -> None:
    bucket = _get_s3_bucket()
    mangas = retrieve_cached_mangas(bucket)

    chapter = None
    for manga in mangas:
        if manga.name == name:
            chapter = manga.chapters.pop(-1)
            break

    if chapter:
        save_cached_mangas(bucket, mangas=mangas)
        logger.info(f"Pop last '{name}' chapter ({chapter})")


if __name__ == "__main__":
    cli()
