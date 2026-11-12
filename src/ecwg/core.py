#!/usr/bin/env python3
"""WitnessGraph pilot: stdlib-only, offline test-conditioned static code localization.

Research demonstration, NOT a Gemma 4 agent or competition-scored implementation.
Graph uses AST-resolved imports and function calls. It is an imperfect static proxy,
not a causal execution trace. All scoring rules are fixed before benchmarking.
"""
from __future__ import annotations
import argparse, ast, json, math, re
from collections import defaultdict, deque
from pathlib import Path


def tokens(s: str) -> set[str]:
    s = re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', s)
    return set(re.findall(r'[a-z0-9]+', s.lower().replace('_', ' '))) - {
        'the', 'a', 'an', 'on', 'for', 'at', 'and', 'to', 'of', 'in', 'with', 'when',
        'should', 'test', 'regression', 'value', 'return', 'def', 'int', 'from',
        'import', 'is', 'not', 'be', 'correct', 'wrong', 'must', 'its', 'by',
    }


def analyze(root: Path) -> tuple[dict, dict]:
    root = Path(root)
    nodes, tree_cache, imports_cache = {}, {}, {}
    for path in root.rglob('*.py'):
        if any(x in path.parts for x in ('__pycache__', '.venv', 'venv')):
            continue
        rel = str(path.relative_to(root)).replace('\\', '/')
        mod = rel[:-3].replace('/', '.')
        if mod.endswith('.__init__'):
            mod = mod[:-9]
        try:
            source = path.read_text(encoding='utf-8')
            tree = ast.parse(source)
        except (UnicodeError, SyntaxError):
            continue
        tree_cache[rel] = (mod, tree, source)
        import_map = {}
        for statement in tree.body:
            if isinstance(statement, ast.ImportFrom):
                base = (statement.module or '')
                if statement.level:
                    prefix = mod.split('.')[:-statement.level]
                    base = '.'.join(prefix + ([base] if base else []))
                for item in statement.names:
                    if item.name != '*':
                        import_map[item.asname or item.name] = base + '.' + item.name
            elif isinstance(statement, ast.Import):
                for item in statement.names:
                    import_map[item.asname or item.name.split('.')[0]] = item.name
        imports_cache[rel] = import_map
        for statement in tree.body:
            if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
                fqn = mod + '.' + statement.name
                snippet = ast.get_source_segment(source, statement) or statement.name
                nodes[fqn] = {'file': rel, 'name': statement.name,
                              'text': snippet[:3000], 'is_test': rel.startswith('tests/')}
    edges = defaultdict(set)
    for rel, (mod, tree, _) in tree_cache.items():
        import_map = imports_cache[rel]
        for fn in tree.body:
            if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            src = mod + '.' + fn.name
            if src not in nodes:
                continue
            for child in ast.walk(fn):
                if not isinstance(child, ast.Call):
                    continue
                name = None
                if isinstance(child.func, ast.Name):
                    name = import_map.get(child.func.id, mod + '.' + child.func.id)
                elif isinstance(child.func, ast.Attribute) and isinstance(child.func.value, ast.Name):
                    base = child.func.value.id
                    name = import_map.get(base, base) + '.' + child.func.attr
                if name in nodes and name != src:
                    edges[src].add(name)
    return nodes, edges


def get_reachable(edges: dict, test_symbol: str, max_depth: int = 4) -> dict:
    distances = {test_symbol: 0}
    queue = deque([test_symbol])
    while queue:
        node = queue.popleft()
        if distances[node] == max_depth:
            continue
        for child in edges.get(node, ()):
            if child not in distances:
                distances[child] = distances[node] + 1
                queue.append(child)
    return distances


def rank(root: Path, issue: str, failing_test_symbol: str, method: str = 'witness') -> list[dict]:
    """Rank production functions without using any ground-truth label or patch."""
    nodes, edges = analyze(root)
    q = tokens(issue + ' ' + failing_test_symbol)
    products = {key: node for key, node in nodes.items() if not node['is_test']}
    raw = {}
    for key, node in products.items():
        # Deliberately elementary lexical baseline, not a fitted BM25 implementation.
        names = tokens(key.replace('.', ' ') + ' ' + (ast.get_docstring(
            ast.parse(node['text']).body[0]) or '' if node['text'].startswith(('def ', 'async def ')) else ''))
        raw[key] = len(q & names) / math.sqrt(max(1, len(names)))
    max_raw = max(raw.values(), default=1.0) or 1.0
    reachable = get_reachable(edges, failing_test_symbol)
    rows = []
    for key, node in products.items():
        lex = raw[key] / max_raw
        on_path = key in reachable and reachable[key] > 0
        # A structural terminal is a node with no observed local outgoing function calls.
        terminal = on_path and len(edges.get(key, ())) == 0
        score = lex if method == 'lexical' else 0.25 * lex + 0.20 * on_path + 0.55 * terminal
        rows.append({'symbol': key, 'file': node['file'], 'score': round(float(score), 6),
                     'lexical': round(float(lex), 6), 'on_test_path': bool(on_path),
                     'terminal': bool(terminal), 'distance': reachable.get(key)})
    rows.sort(key=lambda x: (-x['score'], x['symbol']))
    return rows


