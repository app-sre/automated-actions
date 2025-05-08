from automated_actions_client import AuthenticatedClient
from automated_actions_client.api.v1.me import sync


def test_api_v1_user_me(aa_client: AuthenticatedClient) -> None:
    user = sync(client=aa_client)
    assert user
    assert user.username
