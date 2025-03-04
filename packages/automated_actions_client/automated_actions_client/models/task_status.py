from enum import Enum


class TaskStatus(str, Enum):
    CANCELLED = "cancelled"
    FAILURE = "failure"
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"

    def __str__(self) -> str:
        return str(self.value)
