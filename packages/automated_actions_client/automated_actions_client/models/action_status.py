from enum import Enum


class ActionStatus(str, Enum):
    CANCELLED = "CANCELLED"
    FAILURE = "FAILURE"
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"

    def __str__(self) -> str:
        return str(self.value)
