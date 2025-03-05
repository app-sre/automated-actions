import atexit
import contextlib
import importlib
import logging
import sys
from http.cookiejar import MozillaCookieJar
from importlib.metadata import version
from pathlib import Path
from typing import Annotated, Any

import httpx
import typer
from automated_actions_client import Client
from automated_actions_client.api.v1.me import sync as api_v1_me
from httpx_gssapi import OPTIONAL, HTTPSPNEGOAuth
from rich import print as rich_print
from rich.console import Console

from automated_actions_cli.commands import test
from automated_actions_cli.config import config
from automated_actions_cli.utils import blend_text, progress_spinner

app = typer.Typer(
    pretty_exceptions_show_locals=False,
    rich_markup_mode="rich",
    epilog="Made with [red]:heart:[/red] by [blue]AppSRE[/blue]",
)
app.add_typer(test.app, name="env", help="test related commands.")

logger = logging.getLogger(__name__)

console = Console(record=True)

BANNER = """
    [o_o]
    <)   )╯
     | | |
    (_|_)
-------------------
 AUTOMATED ACTIONS
-------------------
"""


def version_callback(*, value: bool) -> None:
    if value:
        rich_print(f"Version: {version('automated-actions-cli')}")
        raise typer.Exit


class ClientWithCookieJar(Client):
    def get_httpx_client(self) -> httpx.Client:
        """Get the underlying httpx.Client, constructing a new one if not previously set"""
        if self._client is None:
            self._cookiejar = MozillaCookieJar(filename=config.cookies_file)
            with contextlib.suppress(FileNotFoundError):
                self._cookiejar.load()

            self._client = httpx.Client(
                base_url=self._base_url,
                cookies=self._cookiejar,
                headers=self._headers,
                timeout=self._timeout,
                verify=self._verify_ssl,
                follow_redirects=self._follow_redirects,
                **self._httpx_args,
            )
        return self._client

    def __exit__(self, *args: object, **kwargs: Any) -> None:
        # persist cookies
        self._cookiejar.save()
        super().__exit__(*args, **kwargs)
        self._client = None


@app.callback(no_args_is_help=True)
def main(
    ctx: typer.Context,
    *,
    debug: Annotated[bool, typer.Option(help="Enable debug")] = False,
    screen_capture_file: Annotated[Path | None, typer.Option(writable=True)] = None,
    version: Annotated[  # noqa: ARG001
        bool | None, typer.Option(callback=version_callback, help="Display version")
    ] = None,
    quiet: bool = typer.Option(default=False, help="Don't print anything"),
) -> None:
    if "--help" in sys.argv:
        rich_print(
            blend_text(BANNER, (32, 32, 255), (255, 32, 255)),
        )
        # do not initialize the client and everything else if --help is passed
        return

    if not quiet:
        progress = progress_spinner(console=console)
        progress.start()
        progress.add_task(description="Processing...", total=None)
        atexit.register(progress.stop)

    logging.basicConfig(
        level="DEBUG" if config.debug or debug else "INFO",
        format="%(name)-20s: %(message)s",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    ctx.obj = {
        "client": ClientWithCookieJar(
            base_url=str(config.url),
            raise_on_unexpected_status=True,
            follow_redirects=True,
            httpx_args={
                "auth": HTTPSPNEGOAuth(mutual_authentication=OPTIONAL),
            },
        ),
        "console": console,
    }

    # enforce the user to login
    api_v1_me(client=ctx.obj["client"])

    if screen_capture_file is not None:
        rich_print(f"Screen recording: {screen_capture_file}")
        # strip $0 and screen_capture_file option
        args = sys.argv[3:]
        console.print(f"$ automated-actions {' '.join(args)}")
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
