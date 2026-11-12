"""Opt-in patch *proposal* via a user-running local Ollama server.

No model weights are bundled. No external hosted APIs are contacted.
Suggested diffs are untrusted text and never applied automatically.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from .certificates import make_certificate
from .core import analyze, rank

DEFAULT_ENDPOINT = 'http://127.0.0.1:11434/api/chat'
SYSTEM = '''You are a careful offline code-review assistant. Propose ONE minimal fix.
Use only the code and static path evidence given to you. Static call paths do not
prove the source of a bug. Return a unified diff formatted for `git apply` and
nothing else; do not propose edits to tests. If information is insufficient,
write INSUFFICIENT_EVIDENCE instead of guessing.'''


def _check_endpoint(endpoint: str) -> None:
    parsed = urlparse(endpoint)
    if parsed.scheme != 'http' or parsed.hostname not in {'localhost', '127.0.0.1', '::1'}:
        raise ValueError('Only a local http://localhost Ollama endpoint is permitted')
    if parsed.path != '/api/chat':
        raise ValueError('Expected the Ollama /api/chat endpoint')


def build_prompt(root: Path, issue: str, failing_test: str, top_k: int = 3) -> str:
    root = Path(root)
    if not issue.strip():
        raise ValueError('Issue description must be non-empty')
    nodes, _ = analyze(root)
    if failing_test not in nodes or not nodes[failing_test]['is_test']:
        raise ValueError('The failing test must be a discovered test function')
    items = rank(root, issue, failing_test)[:top_k]
    if not items:
        raise ValueError('No production functions discovered in repository')
    sections = [f'ISSUE:\n{issue[:4000]}', f'FAILING TEST: {failing_test}',
                'CANDIDATES (static graph; not confirmed causes):']
    for row in items:
        evidence = 'no directed test-to-target path observed'
        if row['on_test_path']:
            certificate = make_certificate(root, failing_test, row['symbol'])
            evidence = ' -> '.join(certificate['path'])
        code = nodes[row['symbol']]['text'][:3200]
        sections.append(f"Symbol: {row['symbol']}\nFile: {row['file']}\n"
                        f"Path: {evidence}\nSource:\n```python\n{code}\n```")
    return '\n\n'.join(sections)


def propose_patch(root: Path, issue: str, failing_test: str, model: str,
                  endpoint: str = DEFAULT_ENDPOINT, timeout: int = 120) -> str:
    """Request a text diff from an already-installed *local* model.

    The caller must review output before applying. This function is not used
    by the reported experiments and has no guaranteed Gemma 4 compatibility.
    """
    _check_endpoint(endpoint)
    if not model.strip():
        raise ValueError('Specify an installed local model name')
    prompt = build_prompt(root, issue, failing_test)
    payload = {'model': model, 'stream': False, 'options': {'temperature': 0},
               'messages': [{'role': 'system', 'content': SYSTEM},
                            {'role': 'user', 'content': prompt}]}
    request = urllib.request.Request(endpoint, data=json.dumps(payload).encode('utf-8'),
                                     headers={'Content-Type': 'application/json'}, method='POST')
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.load(response)
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError(f'Local model is unavailable: {exc}') from exc
    try:
        content = data['message']['content'].strip()
    except (KeyError, TypeError, AttributeError) as exc:
        raise ValueError('Unexpected Ollama response format') from exc
    if not content:
        raise ValueError('Empty local model response')
    return content
