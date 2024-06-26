import os
import sys
from collections.abc import Callable
from contextlib import contextmanager
from types import TracebackType
from typing import TYPE_CHECKING

from loguru import logger

from platform_input_support.config import settings
from platform_input_support.util.fs import get_full_path

if TYPE_CHECKING:
    from platform_input_support.task import Task


def get_exception_info(record_exception) -> tuple[str, str, str]:
    name = '{name}'
    func = '{function}'
    line = '{line}'

    if record_exception is not None:
        tb: TracebackType
        _, _, tb = record_exception

        if tb is None:
            return name, func, line

        # go back in the stack to the first frame originated inside the app
        app_name = globals()['__package__'].split('.')[0]
        while tb.tb_next:
            next_name = tb.tb_next.tb_frame.f_globals.get('__name__', None)
            if app_name not in next_name:
                break
            name = next_name
            tb = tb.tb_next
        func = tb.tb_frame.f_code.co_name
        line = str(tb.tb_lineno)

    return name, func, line


def get_format_log(include_task: bool = True) -> Callable[..., str]:
    def format_log(record):
        name, func, line = get_exception_info(record.get('exception'))
        task = '<y>{extra[task]}</>::' if include_task and record['extra'].get('task') else ''
        trail = '\n' if include_task else ''

        exception = os.getenv('PIS_SHOW_EXCEPTIONS', 'false').lower() in ['true', '1', 'yes', 'y']

        # debug flag to hide exceptions in logs (they are too verbose when checking the log flow)
        if exception and include_task:
            trail = '\n{exception}'  # noqa: RUF027

        return (
            '<g>{time:YYYY-MM-DD HH:mm:ss.SSS}</> | '
            '<lvl>{level: <8}</> | '
            f'{task}'
            f'<c>{name}</>:<c>{func}</>:<c>{line}</>'
            ' - <lvl>{message}</>'
            f'{trail}'
        )

    return format_log


@contextmanager
def task_logging(task: 'Task'):
    """Context manager that appends log messages to the task's manifest.

    Args:
        task (Task): The task to log messages to.

    Yields:
        None
    """
    with logger.contextualize(task=task.name):
        sink_task = lambda message: task._manifest.log.append(message)
        logger.add(
            sink=sink_task,
            filter=lambda record: record['extra'].get('task') == task.name,
            format=get_format_log(include_task=False),
            level=settings().log_level,
        )

        yield


def init_logger(log_level: str) -> None:
    log_filename = get_full_path('output.log')
    handlers = [
        {
            'sink': sys.stdout,
            'level': log_level,
            'format': get_format_log(),
        },
        {
            'sink': log_filename,
            'level': log_level,
            'serialize': True,
        },
    ]

    logger.remove()
    logger.configure(handlers=handlers)
    logger.debug('logger configured')
