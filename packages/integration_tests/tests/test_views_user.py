from typing import TYPE_CHECKING

from automated_actions_client.api.general import me

if TYPE_CHECKING:
    from automated_actions_client import AuthenticatedClient


def test_api_v1_user_me(aa_client: AuthenticatedClient) -> None:
    user = me.sync(client=aa_client)
    assert user
    assert user.username
