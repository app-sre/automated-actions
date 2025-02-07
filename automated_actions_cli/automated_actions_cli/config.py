from pydantic import HttpUrl
from pydantic_settings import BaseSettings


class Config(BaseSettings):
    # pydantic config
    model_config = {"env_prefix": "aa_"}

    debug: bool = False
    url: HttpUrl = HttpUrl("https://automated-actions.devshift.net")


config = Config()
