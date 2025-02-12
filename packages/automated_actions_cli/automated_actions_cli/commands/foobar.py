import logging

import typer
from rich import print as rich_print

app = typer.Typer()
log = logging.getLogger(__name__)


@app.command()
def test() -> None:
    """Just a test"""
    rich_print("Hello, World!")
