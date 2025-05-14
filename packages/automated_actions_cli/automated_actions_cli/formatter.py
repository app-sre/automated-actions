import json
from collections.abc import Callable
from enum import StrEnum
from typing import Any

import yaml


class OutputFormat(StrEnum):
    """Output format for the command line interface."""

    json = "json"
    yaml = "yaml"


class JsonFormatter:
    def __init__(self, printer: Callable[[str], None], indent: int = 4) -> None:
        self._printer = printer
        self._indent = indent

    def __call__(self, data: Any) -> None:
        """Format the data as JSON."""
        self._printer(json.dumps(data, indent=self._indent, sort_keys=True))


class YamlFormatter:
    def __init__(self, printer: Callable[[str], None], indent: int = 2) -> None:
        self._printer = printer
        self._indent = indent

    def __call__(self, data: Any) -> None:
        """Format the data as yaml."""
        self._printer(
            yaml.dump(
                data,
                indent=self._indent,
                sort_keys=True,
                explicit_start=True,
                default_flow_style=False,
            )
        )
