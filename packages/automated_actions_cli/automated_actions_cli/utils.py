import logging
import shutil
import subprocess

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.text import Text

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
