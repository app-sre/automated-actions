from pydantic import BaseModel


class NoopParam(BaseModel):
    alias: str
    text: str

    # pydantic config
    model_config = {"extra": "ignore"}
