import click
import pytest
from automated_actions_client.schemas import ActionSchemaOut, ActionStatus
from typer.main import get_command

from automated_actions_cli.cli import (
    _get_help_panel,  # noqa: PLC2701
    _serialize_result,  # noqa: PLC2701
    app,
)

click_app = get_command(app)

EXPECTED_COMMANDS = {
    "action-cancel",
    "action-detail",
    "action-list",
    "create-token",
    "external-resource-flush-elasticache",
    "external-resource-rds-reboot",
    "external-resource-rds-snapshot",
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
            assert isinstance(param, click.Option), (
                f"Command '{cmd_name}': param '{param.name}' is a "
                f"{type(param).__name__}, expected Option"
            )


# --- Help panels ---


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
    cmd = click_app.commands[cmd_name]
    assert cmd.rich_help_panel == expected_panel


# --- Specific command parameters ---


def _get_param_names(cmd_name: str) -> set[str]:
    cmd = click_app.commands[cmd_name]
    return {p.name for p in cmd.params} - TYPER_INTERNAL_PARAMS


def test_action_list_params() -> None:
    assert _get_param_names("action-list") == {
        "status",
        "action_user",
        "max_age_minutes",
    }


def test_action_list_status_choices() -> None:
    cmd = click_app.commands["action-list"]
    status_param = next(p for p in cmd.params if p.name == "status")
    assert isinstance(status_param.type, click.Choice)
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
