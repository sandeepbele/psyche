from celery.result import AsyncResult


def check_task_and_children(task_id):
    task = AsyncResult(task_id)
    if task.status not in ('SUCCESS', 'FAILURE'):
        return False
    return all(check_task_and_children(child.id) for child in (task.children or []))
