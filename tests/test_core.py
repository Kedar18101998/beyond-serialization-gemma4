"""Unit tests focus on graph direction, rank determinism, and certificate integrity."""
from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from ecwg import analyze, make_certificate, rank, verify_certificate
from ecwg.certificates import shortest_path
from ecwg.cli import main


class TestResearchCore(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for dir in ['tests', 'lib']:
            (self.root / dir).mkdir()
            (self.root / dir / '__init__.py').write_text('')
        (self.root / 'tests' / 'test_calc.py').write_text(
            'from lib.entry import wrapper\n\ndef test_bug():\n    assert wrapper(3) == 5\n')
        (self.root / 'lib' / 'entry.py').write_text(
            'from lib.engine import calculate\n\ndef wrapper(x):\n    return calculate(x)\n')
        (self.root / 'lib' / 'engine.py').write_text(
            'def calculate(x):\n    """Low-level operation."""\n    return x + 1\n')
        self.test_name = 'tests.test_calc.test_bug'
        self.target = 'lib.engine.calculate'

    def test_expected_directed_edges(self):
        nodes, edges = analyze(self.root)
        self.assertIn(self.test_name, nodes)
        self.assertEqual(edges[self.test_name], {'lib.entry.wrapper'})
        self.assertEqual(edges['lib.entry.wrapper'], {self.target})
        self.assertIsNone(shortest_path(edges, self.target, self.test_name))

    def test_ranking_deterministic(self):
        rows = rank(self.root, 'wrong numerical calculation', self.test_name, 'witness')
        self.assertEqual(rows[0]['symbol'], self.target)
        self.assertEqual(rows, rank(self.root, 'wrong numerical calculation', self.test_name))
        self.assertEqual(len(rows), 2)

    def test_certificate_roundtrip(self):
        cert = make_certificate(self.root, self.test_name, self.target)
        self.assertEqual(cert['path'], [self.test_name, 'lib.entry.wrapper', self.target])
        self.assertTrue(verify_certificate(self.root, cert)[0])
        self.assertIn('static_ast', cert['evidence'])

    def test_certificate_detects_source_mutation(self):
        cert = make_certificate(self.root, self.test_name, self.target)
        (self.root / 'lib/engine.py').write_text('def calculate(x):\n    return x + 2\n')
        valid, errors = verify_certificate(self.root, cert)
        self.assertFalse(valid)
        self.assertTrue(any(e.startswith('changed_file:') for e in errors))

    def test_certificate_rejects_forged_path(self):
        cert = make_certificate(self.root, self.test_name, self.target)
        cert['path'] = [self.test_name, self.target]
        valid, errors = verify_certificate(self.root, cert)
        self.assertFalse(valid)
        self.assertTrue(any(e.startswith('missing_directed_edge:') for e in errors))

    def test_invalid_target_rejected(self):
        with self.assertRaises(ValueError):
            make_certificate(self.root, self.test_name, self.test_name)

    def test_cli_json(self):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            rc = main(['rank', '--root', str(self.root), '--issue', 'calculate bug',
                       '--failing-test', self.test_name])
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(stdout.getvalue())[0]['symbol'], self.target)

    def test_empty_and_truncated_certificate(self):
        self.assertFalse(verify_certificate(self.root, {'schema': 'wrong', 'path': []})[0])


if __name__ == '__main__':
    unittest.main()
