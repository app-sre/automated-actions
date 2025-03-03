from pydantic import BaseModel


class NoopParam(BaseModel):
    alias: str
    description: str = "no description"

    # pydantic config
    model_config = {"extra": "ignore"}
