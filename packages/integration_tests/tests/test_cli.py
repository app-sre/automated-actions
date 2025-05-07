import os
from collections.abc import Callable
from subprocess import CalledProcessError, CompletedProcess, run

import pytest

AACli = Callable[..., CompletedProcess]


@pytest.fixture(autouse=True)
def cli_env() -> None:
    """Set up the environment for the CLI tests."""
    assert os.environ.get("AA_TOKEN") is not None
    assert os.environ.get("AA_URL") is not None


@pytest.fixture
def cli() -> AACli:
    def _run(*args: str) -> CompletedProcess:
        return run(
            ["automated-actions", *args],
            capture_output=True,
            text=True,
            check=True,
        )

    return _run


def test_cli_help(cli: AACli) -> None:
    result = cli("--help")

    assert "Usage:" in result.stdout


def test_cli_me(cli: AACli) -> None:
    result = cli("me")

    assert "UserSchemaOut" in result.stdout
    assert "allowed_actions=" in result.stdout


def test_cli_action_list(cli: AACli) -> None:
    result = cli("action-list")

    assert result.stdout.strip() == "[]"


def test_cli_optional_option_in_help(cli: AACli) -> None:
    result = cli("action-list", "--help")

    assert "--status" in result.stdout
    assert "[default: RUNNING]" in result.stdout


def test_cli_optional_option(cli: AACli) -> None:
    cli("action-list", "--status", "SUCCESS")


def test_cli_required_option_in_help(cli: AACli) -> None:
    result = cli("action-detail", "--help")

    assert "--action-id" in result.stdout
    assert "[required]" in result.stdout


def test_cli_required_option_not_given(cli: AACli) -> None:
    with pytest.raises(CalledProcessError) as e:
        cli("action-detail")

    assert e.value.returncode == 2  # noqa: PLR2004
    assert "Missing option '--action-id'" in e.value.stderr


def test_cli_required_option(cli: AACli) -> None:
    with pytest.raises(CalledProcessError) as e:
        cli("action-detail", "--action-id", "this-id-does-not-exist")

    assert e.value.returncode == 1
    assert '{"detail":"Item not found"}' in e.value.stderr
