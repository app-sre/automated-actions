from unittest.mock import MagicMock

import pytest
from fastapi import Request


@pytest.fixture
def mock_request() -> Request:
    request = MagicMock(spec=Request)
    request.headers = {}

    return request
