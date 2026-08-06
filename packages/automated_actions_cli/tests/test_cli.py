from http.cookiejar import MozillaCookieJar
from typing import TYPE_CHECKING

import click
import pytest
from automated_actions_client.schemas import ActionSchemaOut, ActionStatus
from typer.core import TyperCommand, TyperGroup, TyperOption
from typer.main import get_command

from automated_actions_cli import cli
from automated_actions_cli.cli import (
    _get_help_panel,  # ruff: ignore[import-private-name]
    _serialize_result,  # ruff: ignore[import-private-name]
    app,
    main,
)
from automated_actions_cli.config import Config

if TYPE_CHECKING:
    from pathlib import Path

_cmd = get_command(app)
assert isinstance(_cmd, TyperGroup)
click_app: TyperGroup = _cmd

EXPECTED_COMMANDS = {
    "action-cancel",
    "action-detail",
    "action-list",
    "create-token",
    "external-resource-flush-elasticache",
    "external-resource-rds-reboot",
    "external-resource-rds-snapshot",
    "external-resource-rds-start",
    "external-resource-rds-stop",
    "me",
    "no-op",
    "openshift-trigger-cronjob",
    "openshift-workload-delete",
    "openshift-workload-restart",
}

# Params added by typer itself, not by our registration logic
TYPER_INTERNAL_PARAMS = {"help", "install_completion", "show_completion"}


# --- _get_help_panel ---


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("external_resource_rds_reboot", "Actions"),
        ("external_resource_flush_elasticache", "Actions"),
        ("external_resource_rds_snapshot", "Actions"),
        ("openshift_workload_restart", "Actions"),
        ("openshift_workload_delete", "Actions"),
        ("openshift_trigger_cronjob", "Actions"),
        ("no_op", "Actions"),
        ("action_list", "General"),
        ("action_detail", "General"),
        ("action_cancel", "General"),
        ("me", "General"),
        ("create_token", "Admin"),
        ("unknown_function", "General"),
    ],
)
def test_get_help_panel(name: str, expected: str) -> None:
    assert _get_help_panel(name) == expected


# --- _serialize_result ---


def test_serialize_result_pydantic_model() -> None:
    model = ActionSchemaOut(
        name="test",
        owner="user",
        status=ActionStatus.SUCCESS,
        action_id="abc-123",
        result="ok",
        created_at=1.0,
        updated_at=2.0,
    )
    result = _serialize_result(model)
    assert isinstance(result, dict)
    assert result["status"] == "SUCCESS"
    assert result["action_id"] == "abc-123"


def test_serialize_result_list_of_models() -> None:
    models = [
        ActionSchemaOut(
            name="a",
            owner="u",
            status=ActionStatus.PENDING,
            action_id="1",
            created_at=1.0,
            updated_at=2.0,
        ),
        ActionSchemaOut(
            name="b",
            owner="u",
            status=ActionStatus.FAILURE,
            action_id="2",
            created_at=3.0,
            updated_at=4.0,
        ),
    ]
    result = _serialize_result(models)
    assert isinstance(result, list)
    assert len(result) == len(models)
    assert result[0]["status"] == "PENDING"
    assert result[1]["status"] == "FAILURE"


def test_serialize_result_plain_dict() -> None:
    data = {"key": "value"}
    assert _serialize_result(data) is data


def test_serialize_result_plain_string() -> None:
    assert _serialize_result("hello") == "hello"


# --- Command registration ---


def test_all_commands_registered() -> None:
    registered = set(click_app.commands.keys())
    assert EXPECTED_COMMANDS.issubset(registered)


def test_no_unexpected_commands() -> None:
    registered = set(click_app.commands.keys())
    assert registered == EXPECTED_COMMANDS


def test_all_params_are_options() -> None:
    for cmd_name, cmd in click_app.commands.items():
        for param in cmd.params:
            if param.name in TYPER_INTERNAL_PARAMS:
                continue
            assert isinstance(param, TyperOption), (
                f"Command '{cmd_name}': param '{param.name}' is a "
                f"{type(param).__name__}, expected TyperOption"
            )


# --- Help panels ---


def _get_command(cmd_name: str) -> TyperCommand:
    cmd = click_app.commands[cmd_name]
    assert isinstance(cmd, TyperCommand)
    return cmd


@pytest.mark.parametrize(
    ("cmd_name", "expected_panel"),
    [
        ("external-resource-rds-reboot", "Actions"),
        ("openshift-workload-restart", "Actions"),
        ("no-op", "Actions"),
        ("action-list", "General"),
        ("me", "General"),
        ("create-token", "Admin"),
    ],
)
def test_help_panel(cmd_name: str, expected_panel: str) -> None:
    assert _get_command(cmd_name).rich_help_panel == expected_panel


# --- Specific command parameters ---


def _get_param_names(cmd_name: str) -> set[str]:
    return {
        p.name for p in _get_command(cmd_name).params if p.name
    } - TYPER_INTERNAL_PARAMS


def test_action_list_params() -> None:
    assert _get_param_names("action-list") == {
        "status",
        "action_user",
        "max_age_minutes",
    }


def test_action_list_status_choices() -> None:
    status_param = next(
        p for p in _get_command("action-list").params if p.name == "status"
    )
    assert hasattr(status_param.type, "choices")
    assert set(status_param.type.choices) == {
        "PENDING",
        "RUNNING",
        "SUCCESS",
        "FAILURE",
        "CANCELLED",
    }


def test_external_resource_rds_reboot_params() -> None:
    assert _get_param_names("external-resource-rds-reboot") == {
        "account",
        "identifier",
        "force_failover",
    }


def test_create_token_params() -> None:
    assert _get_param_names("create-token") == {
        "name",
        "username",
        "email",
        "expiration",
    }


def test_me_has_no_params() -> None:
    assert _get_param_names("me") == set()


def test_openshift_workload_delete_params() -> None:
    assert _get_param_names("openshift-workload-delete") == {
        "cluster",
        "namespace",
        "kind",
        "name",
        "api_version",
    }


# --- Kerberos cookie jar persistence ---


def _run_main_with_kerberos_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    """Invoke main() through the Kerberos auth branch with all I/O stubbed out.

    Registers `atexit.register`'d callbacks to run immediately (instead of at
    real process exit) so their effect can be asserted within the test.
    """
    monkeypatch.delenv("AA_TOKEN", raising=False)
    monkeypatch.setattr(cli, "kerberos_available", lambda: True)
    monkeypatch.setattr(cli, "kinit", lambda: None)
    monkeypatch.setattr(cli, "me", lambda: None)
    monkeypatch.setattr(cli.atexit, "register", lambda func, *a, **kw: func(*a, **kw))
    ctx = click.Context(click.Command("test"))
    main(ctx, quiet=True)  # type: ignore[call-arg]


def test_kerberos_auth_persists_cookie_jar_to_disk(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A CLI process authenticating via Kerberos must save the session cookie.

    Without this, every separate CLI invocation starts from an empty cookie
    jar and has to redo the full SSO redirect/token-exchange dance, even
    though the server-side session cookie is still valid.
    """
    cookies_file = tmp_path / "cookies.txt"
    monkeypatch.setattr(Config, "cookies_file", cookies_file)

    _run_main_with_kerberos_auth(monkeypatch)

    assert cookies_file.exists()


def test_kerberos_auth_saves_cookie_jar_ignoring_discard(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The jar must be saved with ignore_discard=True.

    Otherwise a cookie that ever comes back without an explicit expiry (a
    true browser-session cookie) would silently be dropped from the file.
    """
    cookies_file = tmp_path / "cookies.txt"
    monkeypatch.setattr(Config, "cookies_file", cookies_file)

    save_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
    original_save = MozillaCookieJar.save

    def spy_save(self: MozillaCookieJar, *args: object, **kwargs: object) -> None:
        save_calls.append((args, kwargs))
        original_save(self, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(MozillaCookieJar, "save", spy_save)

    _run_main_with_kerberos_auth(monkeypatch)

    assert len(save_calls) == 1
    assert save_calls[0][1].get("ignore_discard") is True
