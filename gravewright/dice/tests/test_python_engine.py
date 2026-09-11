"""Deterministic results captured from the original engine before its removal."""

import json
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from gravewright.dice.engine import RollError, evaluate


def seeded(seed):
    def next_sample():
        nonlocal seed
        seed = (seed * 1664525 + 1013904223) & 0xFFFFFFFF
        return seed / 4294967296

    return next_sample


class PythonEngineTests(TestCase):
    def test_legacy_grammar_results_facts_spans_and_limits(self):
        cases = json.loads(Path(__file__).with_name("legacy_results.json").read_text())
        for case in cases:
            with self.subTest(expression=case["expression"], seed=case["seed"]):
                if "error" in case:
                    with self.assertRaises(RollError):
                        evaluate(case["expression"], random_source=seeded(case["seed"]))
                else:
                    self.assertEqual(
                        evaluate(
                            case["expression"], random_source=seeded(case["seed"])
                        ),
                        case["result"],
                    )

    def test_no_external_process_and_independent_repeat(self):
        with patch(
            "subprocess.run", side_effect=AssertionError("Backend must not start Node")
        ):
            result = evaluate("1d6", repeat=2, random_source=iter([0, 0.99]).__next__)
        self.assertEqual([r["value"]["value"] for r in result], [1, 6])
        self.assertEqual(
            [r["rolls"][0]["facts"][0]["id"] for r in result], ["roll-1", "roll-1"]
        )

    def test_invalid_input_rng_and_function_types(self):
        for expression in [None, 3, " " * 513, "max(1<2, 3)", "clamp(1, 3, 2)"]:
            with self.subTest(expression=expression), self.assertRaises(RollError):
                evaluate(expression)
        for repeat in [0, 13, True, 1.5]:
            with self.subTest(repeat=repeat), self.assertRaises(RollError):
                evaluate("1d6", repeat)
        for sample in [-0.1, 1, float("nan"), float("inf"), True]:
            with self.subTest(sample=sample), self.assertRaises(RollError):
                evaluate("1d6", random_source=lambda sample=sample: sample)
