from pathlib import Path

from appdirs import AppDirs
from pydantic_settings import BaseSettings


class Config(BaseSettings):
    # pydantic config
    model_config = {"env_prefix": "aa_"}

    appdirs: AppDirs = AppDirs("automated-actions", "app-sre")
    pypi_version_cache_expire_minutes: int = 60 * 24  # one day

    @property
    def cookies_file(self) -> Path:
        user_cache_dir = Path(self.appdirs.user_cache_dir)
        user_cache_dir.mkdir(parents=True, exist_ok=True)
        return user_cache_dir / "cookies.txt"

    @property
    def pypi_version_cache(self) -> Path:
        user_cache_dir = Path(self.appdirs.user_cache_dir)
        user_cache_dir.mkdir(parents=True, exist_ok=True)
        return user_cache_dir / "pypi_version_cache"


config = Config()
