from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from ecwg.local_model import _check_endpoint, build_prompt, propose_patch


class TestLocalSuggestion(unittest.TestCase):
    def test_endpoint_restricts_remote_servers(self):
        for url in ['https://api.example.com/api/chat', 'http://8.8.8.8/api/chat',
                    'file:///etc/passwd', 'http://localhost/other']:
            with self.subTest(url=url), self.assertRaises(ValueError):
                _check_endpoint(url)
        _check_endpoint('http://127.0.0.1:11434/api/chat')

    def test_prompt_contains_path_and_candidate_code(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / 'tests').mkdir(); (root / 'lib').mkdir()
            (root/'tests'/'test_example.py').write_text('from lib.entry import calc\n\ndef test_x():\n    assert calc(3) == 5\n')
            (root/'lib'/'entry.py').write_text('def calc(x):\n    return x + 1\n')
            prompt = build_prompt(root, 'wrong calculation', 'tests.test_example.test_x')
            self.assertIn('test_example.test_x', prompt)
            self.assertIn('return x + 1', prompt)
            self.assertIn('lib.entry.calc', prompt)

    def test_model_requires_name_before_network(self):
        with self.assertRaises(ValueError):
            propose_patch('.', 'issue', 'test.test', '', 'http://127.0.0.1:11434/api/chat')


if __name__ == '__main__':
    unittest.main()
