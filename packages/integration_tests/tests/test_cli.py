import json
import os
from collections.abc import Callable
from subprocess import CalledProcessError, CompletedProcess, run
from typing import Literal

import pytest
import yaml

from tests.conftest import Config

AACli = Callable[..., CompletedProcess]


@pytest.fixture
def cli(config: Config) -> AACli:
    os.environ["AA_TOKEN"] = config.token

    def _run(output: Literal["json", "yaml"], *args: str) -> CompletedProcess:
        return run(
            ["automated-actions", "--url", str(config.url), "--output", output, *args],
            capture_output=True,
            text=True,
            check=True,
        )

    return _run


def test_cli_help(cli: AACli) -> None:
    result = cli("json", "--help")

    assert "Usage:" in result.stdout, result.stdout


def test_cli_me(cli: AACli) -> None:
    result = json.loads(cli("json", "me").stdout)

    assert "allowed_actions" in result, result
    assert "name" in result, result


def test_cli_output_yaml(cli: AACli) -> None:
    result = yaml.safe_load(cli("yaml", "me").stdout)

    assert "allowed_actions" in result, result
    assert "name" in result, result


def test_cli_action_list(cli: AACli) -> None:
    result = json.loads(cli("json", "action-list").stdout)

    assert result == [] or "action_id" in result[0], result


def test_cli_optional_option_in_help(cli: AACli) -> None:
    result = cli("json", "action-list", "--help")

    assert "--status" in result.stdout, result.stdout
    assert "[CANCELLED|" in result.stdout, result.stdout
    assert "--action-user" in result.stdout, result.stdout
    assert "--max-age-minutes" in result.stdout, result.stdout


def test_cli_optional_option(cli: AACli) -> None:
    result = json.loads(cli("json", "action-list", "--status", "SUCCESS").stdout)

    assert result == [] or "action_id" in result[0]


def test_cli_required_option_in_help(cli: AACli) -> None:
    result = cli("json", "action-detail", "--help")

    assert "--action-id" in result.stdout, result.stdout
    assert "[required]" in result.stdout, result.stdout


def test_cli_required_option_not_given(cli: AACli) -> None:
    with pytest.raises(CalledProcessError) as e:
        cli("json", "action-detail")

    assert e.value.returncode == 2  # noqa: PLR2004
    assert "Missing option '--action-id'" in e.value.stderr, e.value.stderr


def test_cli_required_option(cli: AACli) -> None:
    with pytest.raises(CalledProcessError) as e:
        cli("json", "action-detail", "--action-id", "this-id-does-not-exist")

    assert e.value.returncode == 1
    assert '{"detail":"Item not found"}' in e.value.stderr, e.value.stderr
