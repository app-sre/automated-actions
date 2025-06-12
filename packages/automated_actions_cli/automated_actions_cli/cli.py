import atexit
import contextlib
import importlib
import logging
import os
import sys
import textwrap
from http.cookiejar import MozillaCookieJar
from importlib.metadata import version
from pathlib import Path
from types import TracebackType
from typing import Annotated, Any

import httpx
import typer
from automated_actions_client import AuthenticatedClient, Client
from automated_actions_client.api.general.me import sync as api_v1_me
from httpx_gssapi import OPTIONAL, HTTPSPNEGOAuth
from packaging.version import parse as parse_version
from rich import print as rich_print
from rich.console import Console

from automated_actions_cli.config import config
from automated_actions_cli.formatter import JsonFormatter, OutputFormat, YamlFormatter
from automated_actions_cli.utils import (
    blend_text,
    get_latest_pypi_version,
    kerberos_available,
    kinit,
    progress_spinner,
)

PACAKGE_NAME = "automated-actions-cli"
LOCAL_VERSION = parse_version(version(PACAKGE_NAME))
# Keep in sync with the tags used by automated-actions FastAPI endpoints.
OPENAPI_TAGS = ["actions", "general", "admin"]

app = typer.Typer(
    pretty_exceptions_show_locals=False,
    rich_markup_mode="rich",
    epilog="Made with [red]:heart:[/red] by [blue]AppSRE[/blue]",
)

logger = logging.getLogger(__name__)

console = Console(record=True, soft_wrap=True)

BANNER = """
    [o_o]
    <)   )╯
     | | |
    (_|_)
-------------------
 AUTOMATED ACTIONS
-------------------
"""


def no_traceback_exception_hook(
    exc_type: type[BaseException],
    exc_value: BaseException,
    tb: TracebackType | None,  # noqa: ARG001
) -> None:
    """Custom exception hook to display exceptions without traceback."""
    rich_print(f"{exc_type.__name__}: {exc_value}", file=sys.stderr)


def version_callback(*, value: bool) -> None:
    if value:
        rich_print(f"Version: {LOCAL_VERSION}")
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
def main(  # noqa: C901, PLR0912
    ctx: typer.Context,
    *,
    url: Annotated[
        str, typer.Option(help="Automated Action Server URL", envvar="AA_URL")
    ] = "https://automated-actions.devshift.net",
    debug: Annotated[
        bool, typer.Option(help="Enable debug", envvar="AA_DEBUG")
    ] = False,
    screen_capture_file: Annotated[
        Path | None,
        typer.Option(
            help="Capture screen recording as SVG",
            writable=True,
            envvar="AA_SCREEN_CAPTURE_FILE",
        ),
    ] = None,
    version: Annotated[  # noqa: ARG001
        bool | None, typer.Option(callback=version_callback, help="Display version")
    ] = None,
    quiet: Annotated[
        bool, typer.Option(help="Don't print anything", envvar="AA_QUIET")
    ] = False,
    output: Annotated[
        OutputFormat, typer.Option(help="Output format", envvar="AA_OUTPUT")
    ] = OutputFormat.yaml,
    color: Annotated[
        bool, typer.Option(help="Use colored output", envvar="AA_COLOR")
    ] = True,
) -> None:
    if "--help" in sys.argv:
        rich_print(
            blend_text(BANNER, (32, 32, 255), (255, 32, 255)),
        )
        # do not initialize the client and everything else if --help is passed
        return

    progress = None
    if not quiet and not screen_capture_file:
        if get_latest_pypi_version(PACAKGE_NAME) > LOCAL_VERSION:
            rich_print(
                textwrap.dedent(f"""
                    [red]You're running an outdated version of {PACAKGE_NAME}![/red]
                    Please update to the latest version to benefit from new features and bug fixes.
                """)
            )
        progress = progress_spinner(console=console)
        progress.start()
        progress.add_task(description="Processing...", total=None)
        atexit.register(progress.stop)

    logging.basicConfig(
        level="DEBUG" if debug else "INFO",
        format="%(name)-20s: %(message)s",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)

    if not debug:
        sys.excepthook = no_traceback_exception_hook

    if token := os.environ.get("AA_TOKEN"):
        ctx.obj = {
            "client": AuthenticatedClient(
                base_url=str(url),
                token=token,
                raise_on_unexpected_status=True,
                follow_redirects=True,
            )
        }

    elif kerberos_available():
        if progress:
            progress.stop()
        kinit()
        if progress:
            progress.start()

        ctx.obj = {
            "client": ClientWithCookieJar(
                base_url=str(url),
                raise_on_unexpected_status=True,
                follow_redirects=True,
                httpx_args={
                    "auth": HTTPSPNEGOAuth(mutual_authentication=OPTIONAL),
                },
            )
        }
    else:
        logger.error(
            "No bearer token or Kerberos authentication available. Please set AA_TOKEN or install and configure Kerberos."
        )
        raise typer.Exit(1)

    printer = console.print if color else print
    match output:
        case OutputFormat.json:
            ctx.obj["formatter"] = JsonFormatter(printer=printer)
        case OutputFormat.yaml:
            ctx.obj["formatter"] = YamlFormatter(printer=printer)
        case _:
            raise ValueError("Invalid output format")

    # enforce the user to login
    api_v1_me(client=ctx.obj["client"])

    if screen_capture_file is not None:
        screen_capture_file = screen_capture_file.with_suffix(".svg")
        rich_print(f"Screen recording: {screen_capture_file}")
        # strip $0 and screen_capture_file option
        args = sys.argv[3:]
        console.print(f"$ automated-actions {' '.join(args)}")
        # title = command sub_command
        title = " ".join(args[0:2])
        atexit.register(console.save_svg, str(screen_capture_file), title=title)


def initialize_client_actions() -> None:
    """Initialize typer commands from all available automated-actions-client actions."""
    for module in OPENAPI_TAGS:
        for action in dir(
            importlib.import_module(f"automated_actions_client.api.{module}")
        ):
            if not action.startswith("_"):
                app.add_typer(
                    importlib.import_module(
                        f"automated_actions_client.api.{module}.{action}"
                    ).app
                )


initialize_client_actions()
