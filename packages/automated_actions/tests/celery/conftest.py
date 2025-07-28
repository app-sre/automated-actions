from time import time
from unittest.mock import Mock

import pytest
from automated_actions_utils.cluster_connection import ClusterConnectionData
from automated_actions_utils.openshift_client import (
    OpenshiftClient,
)
from pytest_mock import MockerFixture

from automated_actions.db.models import Action


@pytest.fixture
def mock_oc(mocker: MockerFixture) -> Mock:
    return mocker.Mock(spec=OpenshiftClient)


@pytest.fixture
def mock_action(mocker: MockerFixture) -> Mock:
    return mocker.Mock(spec=Action, created_at=time())


@pytest.fixture
def cluster_connection_data() -> ClusterConnectionData:
    return ClusterConnectionData(url="url", token="token")  # noqa: S106
