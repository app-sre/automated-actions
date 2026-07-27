def test_config_import_settings() -> None:
    from automated_actions.config import (  # ruff: ignore[import-outside-top-level]
        settings,
    )

    # we don't need to test all settings because ruff and mypy will do that for us
    assert settings.environment == "unit_tests"
