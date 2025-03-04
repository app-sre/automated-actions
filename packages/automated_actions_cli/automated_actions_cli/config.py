from pathlib import Path

from appdirs import AppDirs
from pydantic import HttpUrl
from pydantic_settings import BaseSettings


class Config(BaseSettings):
    # pydantic config
    model_config = {"env_prefix": "aa_"}

    debug: bool = False
    url: HttpUrl = HttpUrl("https://automated-actions.devshift.net")
    appdirs: AppDirs = AppDirs("automated-actions", "app-sre")

    @property
    def cookies_file(self) -> Path:
        user_cache_dir = Path(self.appdirs.user_cache_dir)
        user_cache_dir.mkdir(parents=True, exist_ok=True)
        return user_cache_dir / "cookies.txt"


config = Config()
