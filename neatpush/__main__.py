from typing import Any, Optional

import structlog
import typer
import uvicorn

from .app import check_new_chapters

logger = structlog.getLogger("neatpush")

cli = typer.Typer()


@cli.command("serve")
def run_server(
    port: int = typer.Option(8000, help="port to use"),
    host: str = typer.Option("127.0.0.1", help="host to use"),
    watch: Optional[bool] = typer.Option(None, "--watch/--no-watch"),
) -> None:
    kwargs: dict[str, Any] = {
        "port": port,
        "host": host,
        "app": "neatpush.app:app",
        "reload": watch,
    }
    uvicorn.run(**kwargs)


@cli.command("run")
def run() -> None:
    check_new_chapters()


if __name__ == "__main__":
    cli()
