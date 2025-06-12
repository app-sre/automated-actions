from pathlib import Path
from tempfile import mkdtemp

from appdirs import AppDirs
from pydantic_settings import BaseSettings


class Config(BaseSettings):
    # pydantic config
    model_config = {"env_prefix": "aa_"}

    appdirs: AppDirs = AppDirs("automated-actions", "app-sre")
    pypi_version_cache_expire_minutes: int = 60 * 24  # one day

    @property
    def user_cache_dir(self) -> Path:
        user_cache_dir = Path(self.appdirs.user_cache_dir)
        try:
            user_cache_dir.mkdir(parents=True, exist_ok=True)
            return user_cache_dir
        except PermissionError:
            # If we cannot create the user cache directory, we fall back to an ordinary tmp directory.
            return Path(mkdtemp(prefix="automated-actions-cache-"))

    @property
    def cookies_file(self) -> Path:
        return self.user_cache_dir / "cookies.txt"

    @property
    def pypi_version_cache(self) -> Path:
        return self.user_cache_dir / "pypi_version_cache"


config = Config()
