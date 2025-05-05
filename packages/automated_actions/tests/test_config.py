def test_config_import_settings() -> None:
    from automated_actions.config import settings  # noqa: PLC0415

    # we don't need to test all settings because ruff and mypy will do that for us
    assert settings.debug is False
