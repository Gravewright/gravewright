# Gravewright dice — Python runtime

[English](ARCHITECTURE.md) · [Português](ARCHITECTURE.pt-BR.md)

All server evaluation runs in Python. `engine.py` validates input and concurrency,
then invokes this package. There are no Node subprocesses, JavaScript engine
files, TypeScript sources or TypeScript compilation steps.

- `parser.py`: recursive descent with the original operator precedence,
  lexical attachment of dice modifiers and source spans.
- `compiler.py`: numeric/boolean type rules, allowed functions, deterministic
  pool thresholds and complexity limits; no randomness is consumed here.
- `runtime.py`: left-to-right expression evaluation, stable keep/drop ordering,
  breadth-first explosion/reroll queues and bounded fact generation.
- `errors.py`: the `RollError` exception exposed to the Django integration.

`compile_expression` validates an in-memory notation tree. It does not compile
source files or produce an executable artifact. The executor emits dice plans
inside the existing JSON result for compatibility with persisted history.

## Results and randomness

The result retains schema `gravewright-dice-result`, version 1, values, plans,
facts, source spans, selection states and comparison traces. Facts preserve
IDs, physical face indexes, causes, lineage and normalized entropy. Selection
and generation preserve prior facts; history renders the stored JSON without
invoking the RNG again.

Production samples use Python `secrets`. A callable RNG can be injected by tests;
clients cannot select it through WebSocket payloads. Each independent repetition
gets a fresh executor and result ID sequence. Standard numeric functions retain
the original semantics, including rounding ties toward positive infinity.

## Resource bounds

Input length is at most 512 characters, with syntactic nesting 32. Compilation
checks 1,000 nodes, semantic depth 128 and 100 arguments per function call.
Execution permits 99 initial dice per term, 1,000 faces, 256 initial dice per
expression, 32 dice terms, 256 generated results per term and 512 facts per
expression. Up to 12 independent repetitions are accepted. Four evaluations may
run simultaneously per process. No unbounded recursive explosion is possible.

## Parity evidence

`../tests/legacy_results.json` records 396 deterministic cases from the original
engine. Python tests compare complete JSON results and rejection of invalid
expressions. Additional tests ensure independent repetitions, valid random
samples and evaluation without external processes.
