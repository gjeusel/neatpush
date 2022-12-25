import asyncio
import logging
from typing import Any

import boto3
import structlog
import typer

from . import clients
from .config import CFG

logger = structlog.getLogger("neatpush")

cli = typer.Typer()


@cli.command("msg")
def send_message(message: str = "Hello") -> None:
    pass


if __name__ == "__main__":
    cli()
