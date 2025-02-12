import atexit
import importlib
import logging
import sys
from importlib.metadata import version
from pathlib import Path
from typing import Annotated

import typer
from automated_actions_client import Client
from rich import print as rich_print
from rich.console import Console
from rich.logging import RichHandler

from automated_actions_cli.commands import test
from automated_actions_cli.config import config

app = typer.Typer()
app.add_typer(test.app, name="env", help="test related commands.")


console = Console(record=True)


def version_callback(*, value: bool) -> None:
    if value:
        rich_print(f"Version: {version('automated-actions-cli')}")
        raise typer.Exit


@app.callback(no_args_is_help=True)
def main(
    ctx: typer.Context,
    *,
    debug: Annotated[bool, typer.Option(help="Enable debug")] = False,
    screen_capture_file: Annotated[Path | None, typer.Option(writable=True)] = None,
    version: Annotated[  # noqa: ARG001
        bool | None, typer.Option(callback=version_callback, help="Display version")
    ] = None,
) -> None:
    logging.basicConfig(
        level="DEBUG" if config.debug or debug else "INFO",
        format="%(name)-20s: %(message)s",
        datefmt="[%X]",
        handlers=[RichHandler()],
    )
    ctx.obj = {
        "client": Client(
            base_url="http://localhost:8080", raise_on_unexpected_status=True
        )
    }
    if screen_capture_file is not None:
        rich_print(f"Screen recording: {screen_capture_file}")
        # strip $0 and screen_capture_file option
        args = sys.argv[3:]
        console.print(f"$ qd {' '.join(args)}")
        # title = command sub_command
        title = " ".join(args[0:2])
        atexit.register(
            console.save_svg, str(screen_capture_file.with_suffix(".svg")), title=title
        )


def initialize_client_actions() -> None:
    """Initialize typer commands from all available automated-actions-client actions."""
    for action in dir(importlib.import_module("automated_actions_client.api.v1")):
        if not action.startswith("_"):
            app.add_typer(
                importlib.import_module(f"automated_actions_client.api.v1.{action}").app
            )


initialize_client_actions()
