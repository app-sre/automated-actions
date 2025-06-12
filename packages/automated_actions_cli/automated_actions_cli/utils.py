import logging
import shutil
import subprocess

import httpx
from diskcache import Cache
from packaging.version import Version
from packaging.version import parse as parse_version
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.text import Text

from automated_actions_cli.config import config

logger = logging.getLogger(__name__)


def blend_text(
    message: str, color1: tuple[int, int, int], color2: tuple[int, int, int]
) -> Text:
    """Blend text from one color to another."""
    text = Text(message)
    r1, g1, b1 = color1
    r2, g2, b2 = color2
    dr = r2 - r1
    dg = g2 - g1
    db = b2 - b1
    size = len(text)
    for index in range(size):
        blend = index / size
        color = f"#{int(r1 + dr * blend):2X}{int(g1 + dg * blend):2X}{int(b1 + db * blend):2X}"
        text.stylize(color, index, index + 1)
    return text


def progress_spinner(console: Console) -> Progress:
    """Display shiny progress spinner."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    )


def kerberos_available() -> bool:
    return bool(shutil.which("kinit"))


def kinit() -> None:
    """Acquire a kerberos ticket if needed."""
    try:
        # Check if the kerberos ticket is valid
        subprocess.run(["klist", "-s"], check=True, capture_output=True)
    except subprocess.CalledProcessError:
        # If the ticket is not valid, acquire a new one
        subprocess.run(["kinit"], check=True, capture_output=False)


def get_latest_pypi_version(package_name: str) -> Version:
    """Get the latest version of a package from PyPI."""
    pypi_version_cache = Cache(directory=str(config.pypi_version_cache))
    version_str = "0.0.0"
    if package_name not in pypi_version_cache:
        try:
            response = httpx.get(
                f"https://pypi.org/pypi/{package_name}/json", timeout=5
            )
            response.raise_for_status()
            version_str = response.json().get("info", {}).get("version", version_str)
        except httpx.RequestError:
            # ignore network errors
            pass
    else:
        version_str = pypi_version_cache[package_name]

    # cache the version string
    pypi_version_cache.set(
        package_name,
        version_str,
        expire=config.pypi_version_cache_expire_minutes * 60,
    )

    return parse_version(version_str)
