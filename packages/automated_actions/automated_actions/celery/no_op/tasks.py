from automated_actions.celery.app import app
from automated_actions.celery.automated_action_task import AutomatedActionTask
from automated_actions.db.models import Action


@app.task(base=AutomatedActionTask)
def no_op(action: Action) -> None:
    pass
