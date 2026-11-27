"""Python entry point for the VTT's own dice grammar; no external process."""

from threading import BoundedSemaphore

from .grammar.compiler import compile_expression
from .grammar.errors import RollError
from .grammar.parser import Parser
from .grammar.runtime import Executor
from .grammar import runtime
from .grammar.compiler import children

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


def evaluate_batch(expressions, *, random_source=None):
    """Evaluate a bounded heterogeneous batch, compiling every input first.

    This is a persistence-free engine primitive. Its caller owns authorization,
    the transaction, result size limits and receipts. One batch occupies one
    engine slot; aggregate limits also bound time spent holding a write lock.
    """
    if not isinstance(expressions, list) or not 1 <= len(expressions) <= 64:
        raise RollError('Choose between 1 and 64 expressions.')
    if not _SLOTS.acquire(blocking=False):
        raise RollError('Too many rolls are in progress. Try again.')
    try:
        plans, nodes, initial = [], 0, 0
        for expression in expressions:
            if not isinstance(expression, str) or not expression.strip() or len(expression) > 512:
                raise RollError('The expression must contain 1 to 512 characters.')
            plan = compile_expression(Parser(expression).parse())
            stack = [plan]
            while stack:
                node = stack.pop()
                nodes += 1
                if node['kind'] == 'dice':
                    initial += node['count']
                if nodes > 4096 or initial > 1024:
                    raise RollError('Batch exceeds the limit of 4096 nodes or 1024 initial dice.')
                stack.extend(children(node))
            plans.append(plan)
        draws = 0

        def sample():
            nonlocal draws
            if draws >= 2048:
                raise RollError('Batch exceeds the limit of 2048 dice facts.')
            draws += 1
            return (random_source or runtime.secure_sample)()

        return [Executor(sample).execute(plan) for plan in plans]
    finally:
        _SLOTS.release()
