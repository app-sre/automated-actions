from time import time
from typing import TYPE_CHECKING

import pytest
from automated_actions_utils.cluster_connection import ClusterConnectionData
from automated_actions_utils.openshift_client import (
    OpenshiftClient,
)

from automated_actions.db.models import Action

if TYPE_CHECKING:
    from unittest.mock import Mock

    from pytest_mock import MockerFixture


@pytest.fixture
def mock_oc(mocker: MockerFixture) -> Mock:
    return mocker.Mock(spec=OpenshiftClient)


@pytest.fixture
def mock_action(mocker: MockerFixture) -> Mock:
    return mocker.Mock(spec=Action, created_at=time())


@pytest.fixture
def cluster_connection_data() -> ClusterConnectionData:
    return ClusterConnectionData(url="url", token="token")  # noqa: S106
