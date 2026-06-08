import atexit
import contextlib
import enum
import inspect
import logging
import os
import sys
import textwrap
import typing
from http.cookiejar import MozillaCookieJar
from importlib.metadata import version
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any

import pydantic
import typer
from automated_actions_client import client as client_module
from automated_actions_client import schemas as client_schemas
from automated_actions_client.client import client as aa_client
from automated_actions_client.client import me
from automated_actions_client.config import Config
from clientele.http import httpx_backend
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

from ._gssapi import OPTIONAL, HTTPSPNEGOAuth

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import TracebackType

PACAKGE_NAME = "automated-actions-cli"
LOCAL_VERSION = parse_version(version(PACAKGE_NAME))

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
    msg = str(exc_value)
    if not msg and hasattr(exc_value, "response"):
        resp = exc_value.response
        try:
            detail = resp.json().get("detail", resp.text)
        except ValueError, AttributeError:
            detail = resp.text
        msg = f"HTTP {resp.status_code}: {detail}"
    rich_print(f"{exc_type.__name__}: {msg}", file=sys.stderr)


def version_callback(*, value: bool) -> None:
    if value:
        rich_print(f"Version: {LOCAL_VERSION}")
        raise typer.Exit


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
    ctx.ensure_object(dict)

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
    logging.getLogger("httpx2").setLevel(logging.WARNING)

    if not debug:
        sys.excepthook = no_traceback_exception_hook

    if token := os.environ.get("AA_TOKEN"):
        aa_client.configure(
            config=Config(
                base_url=str(url),
                headers={"Authorization": f"Bearer {token}"},
                follow_redirects=True,
                timeout=15,
            )
        )

    elif kerberos_available():
        if progress:
            progress.stop()
        kinit()
        if progress:
            progress.start()

        cookiejar = MozillaCookieJar(filename=config.cookies_file)
        with contextlib.suppress(FileNotFoundError):
            cookiejar.load()

        aa_client.configure(
            config=Config(
                base_url=str(url),
                http_backend=httpx_backend.HttpxHTTPBackend(
                    client_options={
                        "cookies": cookiejar,
                        "auth": HTTPSPNEGOAuth(mutual_authentication=OPTIONAL),
                        "follow_redirects": True,
                        "base_url": str(url),
                    }
                ),
            )
        )

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
    me()

    if screen_capture_file is not None:
        screen_capture_file = screen_capture_file.with_suffix(".svg")
        rich_print(f"Screen recording: {screen_capture_file}")
        # strip $0 and screen_capture_file option
        args = sys.argv[3:]
        console.print(f"$ automated-actions {' '.join(args)}")
        # title = command sub_command
        title = " ".join(args[0:2])
        atexit.register(console.save_svg, str(screen_capture_file), title=title)


def _get_help_panel(name: str) -> str:
    """Map function name to help panel group, matching FastAPI endpoint tags."""
    if name.startswith(("external_resource_", "openshift_")) or name == "no_op":
        return "Actions"
    if name == "create_token":
        return "Admin"
    return "General"


def _serialize_result(result: object) -> object:
    """Convert pydantic models to serializable dicts."""
    if isinstance(result, pydantic.BaseModel):
        return result.model_dump(mode="json")
    if isinstance(result, list):
        return [_serialize_result(item) for item in result]
    return result


def _build_typer_params(
    sig: inspect.Signature,
    hints: dict[str, Any],
    data_model: type[pydantic.BaseModel] | None,
) -> tuple[list[inspect.Parameter], dict[str, Any]]:
    """Build typer parameter list and annotations from a client function signature."""
    new_params: list[inspect.Parameter] = [
        inspect.Parameter(
            "ctx", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=typer.Context
        )
    ]
    new_annotations: dict[str, Any] = {"ctx": typer.Context, "return": None}

    for pname, param in sig.parameters.items():
        if pname == "data":
            if data_model:
                for field_name, field_info in data_model.model_fields.items():
                    ft = field_info.annotation or str
                    annotation = Annotated[ft, typer.Option()]  # type: ignore[valid-type]
                    default = (
                        inspect.Parameter.empty
                        if field_info.is_required()
                        else field_info.default
                    )
                    new_params.append(
                        inspect.Parameter(
                            field_name,
                            inspect.Parameter.KEYWORD_ONLY,
                            default=default,
                            annotation=annotation,
                        )
                    )
                    new_annotations[field_name] = annotation
            continue

        resolved = hints.get(pname, param.annotation)
        annotation = Annotated[resolved, typer.Option()]  # type: ignore[misc]
        default = (
            param.default
            if param.default is not inspect.Parameter.empty
            else inspect.Parameter.empty
        )
        new_params.append(
            inspect.Parameter(
                pname,
                inspect.Parameter.KEYWORD_ONLY,
                default=default,
                annotation=annotation,
            )
        )
        new_annotations[pname] = annotation

    return new_params, new_annotations


def _register_client_command(
    name: str,
    func: Callable[..., Any],
    type_ns: dict[str, Any],
) -> None:
    """Register a single client function as a typer command."""
    sig = inspect.signature(func)
    hints = typing.get_type_hints(func, localns=type_ns)

    data_hint = hints.get("data")
    skip_data = data_hint is type(None)
    data_model: type[pydantic.BaseModel] | None = None
    if inspect.isclass(data_hint) and issubclass(data_hint, pydantic.BaseModel):
        data_model = data_hint

    new_params, new_annotations = _build_typer_params(sig, hints, data_model)
    new_sig = sig.replace(parameters=new_params, return_annotation=None)

    def wrapper(ctx: typer.Context, **kwargs: Any) -> None:
        call_kwargs = {
            k: v.value if isinstance(v, enum.Enum) else v for k, v in kwargs.items()
        }
        if skip_data:
            call_kwargs["data"] = None
        elif data_model:
            data_fields = {
                f: call_kwargs.pop(f)
                for f in data_model.model_fields
                if f in call_kwargs
            }
            call_kwargs["data"] = data_model(**data_fields)
        try:
            result = func(**call_kwargs)
        except Exception as e:
            if hasattr(e, "response"):
                rich_print(e.response.text, file=sys.stderr)
                raise typer.Exit(1) from None
            raise
        ctx.obj["formatter"](_serialize_result(result))

    wrapper.__signature__ = new_sig  # type: ignore[attr-defined]
    wrapper.__annotations__ = new_annotations
    wrapper.__name__ = name
    wrapper.__qualname__ = name
    wrapper.__doc__ = func.__doc__

    app.command(rich_help_panel=_get_help_panel(name))(wrapper)


def initialize_client_actions() -> None:
    """Initialize typer commands from all available automated-actions-client actions."""
    ns = vars(client_schemas)

    for name, func in inspect.getmembers(client_module, inspect.isfunction):
        if name.startswith("_"):
            continue
        _register_client_command(name, func, ns)


initialize_client_actions()
