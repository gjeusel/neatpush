from bdb import BdbQuit
from typing import Any, Optional

import structlog
import typer
import uvicorn

from . import manga
from .notify import send_sms

logger = structlog.getLogger("neatpush")

cli = typer.Typer()


@cli.command("sms")
def _send_sms(message: str = typer.Option("Hello", help="SMS content.")) -> None:
    response = send_sms(message)
    logger.info("SMS Sent.", payload=response)


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
def run(debug: Optional[bool] = typer.Option(None, "--debug/--no-debug")) -> None:
    if debug:
        try:
            manga.get_new_chapters()
        except BdbQuit:
            pass
        except Exception:
            __import__("pdb").post_mortem()  # POSTMORTEM
    else:
        manga.get_new_chapters()


if __name__ == "__main__":
    cli()
