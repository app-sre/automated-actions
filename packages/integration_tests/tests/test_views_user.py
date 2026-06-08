from automated_actions_client.client import me


def test_api_v1_user_me() -> None:
    user = me()
    assert user is not None
    assert user.username
