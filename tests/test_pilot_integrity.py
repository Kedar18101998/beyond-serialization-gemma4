"""Expected toy-dataset outcomes: not a held-out SWE benchmark."""
from __future__ import annotations
import json
import unittest
from pathlib import Path
from ecwg import rank

ROOT = Path(__file__).resolve().parents[1]


class TestPilotIntegrity(unittest.TestCase):
    def test_results_match_source_for_every_case(self):
        results = json.loads((ROOT/'results/pilot_results.json').read_text())
        self.assertEqual(len(results['cases']), 16)
        for case in results['cases']:
            root = ROOT/'data/synthetic_cases'/case['id']
            for method, key in [('lexical','lexical_rank'), ('witness','witness_rank')]:
                items = rank(root, case['issue'], case['failing_test'], method)
                actual = next((i + 1 for i, row in enumerate(items)
                               if row['symbol'] == case['ground_truth_symbol']), None)
                self.assertEqual(actual, case[key], (case['id'], method))


if __name__ == '__main__':
    unittest.main()
