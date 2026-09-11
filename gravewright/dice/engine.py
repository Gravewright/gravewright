"""Python entry point for the VTT's own dice grammar; no external process."""

from threading import BoundedSemaphore

from .grammar.compiler import compile_expression
from .grammar.errors import RollError
from .grammar.parser import Parser
from .grammar.runtime import Executor

_SLOTS = BoundedSemaphore(4)


def evaluate(expression, repeat=1, *, random_source=None):
    """Parse, validate and evaluate bounded dice expressions without persistence.
    
    Return a result dictionary, or a list for repeated rolls. random_source is
    a callable for deterministic tests; the transport does not expose it."""
    if (
        not isinstance(expression, str)
        or not expression.strip()
        or len(expression) > 512
    ):
        raise RollError("The expression must contain 1 to 512 characters.")
    if type(repeat) is not int or not 1 <= repeat <= 12:
        raise RollError("Choose between 1 and 12 independent rolls.")
    if not _SLOTS.acquire(blocking=False):
        raise RollError("Too many rolls are in progress. Try again.")
    try:
        plan = compile_expression(Parser(expression).parse())
        results = [Executor(random_source).execute(plan) for _ in range(repeat)]
        return results[0] if repeat == 1 else results
    finally:
        _SLOTS.release()
