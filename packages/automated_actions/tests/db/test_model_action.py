# ruff: noqa: ARG003
from __future__ import annotations

import pytest

from automated_actions.db.models import (
    ActionManager,
    ActionSchemaIn,
    ActionSchemaOut,
    ActionStatus,
    get_action_manager,
)


class ActionStub(ActionSchemaOut):
    """Stub for Action model."""

    def dump(self) -> ActionSchemaOut:
        return self

    @classmethod
    def find_by_owner(
        cls, username: str, status: ActionStatus | None
    ) -> list[ActionStub]:
        """Stub method to return a list of actions."""
        return [ACTION]

    @classmethod
    def get_or_404(cls, action_id: str) -> ActionStub:
        """Stub method to return an action by its primary key."""
        return ACTION

    def set_status(self, status: ActionStatus) -> None:
        """Stub method to set the status of an action."""

    @classmethod
    def create(cls, params: ActionSchemaIn) -> ActionStub:
        return ACTION


ACTION = ActionStub(
    action_id="1",
    name="test action",
    status="RUNNING",
    result="test result",
    owner="owner_email",
    created_at=1.0,
    updated_at=2.0,
)


@pytest.fixture
def action_mgr() -> ActionManager[ActionStub]:
    """Fixture to get the action manager."""
    return ActionManager[ActionStub](ActionStub)


def test_model_action_get_action_manager() -> None:
    assert isinstance(get_action_manager(), ActionManager)


def test_model_action_action_manager(action_mgr: ActionManager) -> None:
    assert isinstance(action_mgr, ActionManager)
    assert action_mgr.klass == ActionStub


def test_model_action_action_manager_get_user_actions(
    action_mgr: ActionManager,
) -> None:
    assert action_mgr.get_user_actions("fake", ActionStatus.RUNNING) == [ACTION]


def test_model_action_action_manager_get_or_404(action_mgr: ActionManager) -> None:
    assert action_mgr.get_or_404("fake") == ACTION


def test_model_action_action_manager_create_action(action_mgr: ActionManager) -> None:
    class User:
        username = "owner_email"

    owner = User()
    assert action_mgr.create_action("fake", owner) == ACTION
