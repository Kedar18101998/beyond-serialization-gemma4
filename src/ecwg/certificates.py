"""Static graph evidence certificates.

A certificate proves only that a claimed path exists in the AST-derived graph
and that the referenced source files have not changed since it was created.
It cannot establish that a patch is correct or that an edge executed at runtime.
"""
from __future__ import annotations

from collections import deque
from hashlib import sha256
from pathlib import Path
from typing import Any

from .core import analyze

SCHEMA = 'ecwg.static-call-path.v1'


def shortest_path(edges: dict[str, set[str]], start: str, end: str) -> list[str] | None:
    if start == end:
        return [start]
    seen = {start}
    todo = deque([(start, [start])])
    while todo:
        node, path = todo.popleft()
        for nxt in sorted(edges.get(node, ())):
            if nxt in seen:
                continue
            if nxt == end:
                return path + [nxt]
            seen.add(nxt)
            todo.append((nxt, path + [nxt]))
    return None


def _digest(root: Path, rel_path: str) -> str:
    # Each relative path is derived from our Python AST scanner, never user input.
    absolute = (root / rel_path).resolve()
    absolute.relative_to(root.resolve())
    return sha256(absolute.read_bytes()).hexdigest()


def make_certificate(root: Path, failing_test: str, target: str) -> dict[str, Any]:
    """Record an auditable directed test-to-target path and file hashes."""
    root = Path(root)
    nodes, edges = analyze(root)
    if failing_test not in nodes or not nodes[failing_test]['is_test']:
        raise ValueError(f'Not a discovered test function: {failing_test}')
    if target not in nodes or nodes[target]['is_test']:
        raise ValueError(f'Not a discovered production function: {target}')
    path = shortest_path(edges, failing_test, target)
    if not path or len(path) < 2:
        raise ValueError('No directed call path from failing test to target')
    file_list = sorted({nodes[symbol]['file'] for symbol in path})
    return {
        'schema': SCHEMA,
        'evidence': 'static_ast_call_graph_not_runtime_or_patch_proof',
        'failing_test': failing_test,
        'target': target,
        'path': path,
        'files_sha256': {file: _digest(root, file) for file in file_list},
    }


def verify_certificate(root: Path, certificate: dict[str, Any]) -> tuple[bool, list[str]]:
    """Verify path edges, endpoint roles, and all source hashes.

    Never treat certificates as trusted signatures: an attacker may rewrite both
    source and hashes. This detects stale/tampered files against a given record.
    """
    root = Path(root)
    errors: list[str] = []
    nodes, edges = analyze(root)
    if certificate.get('schema') != SCHEMA:
        errors.append('unsupported_schema')
    path = certificate.get('path')
    if not isinstance(path, list) or len(path) < 2 or any(not isinstance(x, str) for x in path):
        return False, errors + ['invalid_path']
    start = certificate.get('failing_test')
    target = certificate.get('target')
    if path[0] != start or path[-1] != target:
        errors.append('endpoint_mismatch')
    if start not in nodes or not nodes[start]['is_test']:
        errors.append('test_not_found')
    if target not in nodes or nodes[target]['is_test']:
        errors.append('production_target_not_found')
    for source, destination in zip(path, path[1:]):
        if source not in nodes or destination not in edges.get(source, ()):
            errors.append(f'missing_directed_edge:{source}->{destination}')
    hashes = certificate.get('files_sha256')
    if not isinstance(hashes, dict):
        return False, errors + ['hashes_missing']
    expected_files = {nodes[s]['file'] for s in path if s in nodes}
    if set(hashes) != expected_files:
        errors.append('file_set_mismatch')
    for file in sorted(expected_files):
        try:
            if hashes.get(file) != _digest(root, file):
                errors.append(f'changed_file:{file}')
        except (OSError, ValueError):
            errors.append(f'unreadable_file:{file}')
    return (not errors), errors
