#!/usr/bin/env python3
"""Create/re-run a 16-case, fully reproducible synthetic cross-file stress test.

Twelve deep-implementation faults and four entrypoint faults are intentionally
included. The mixture is NOT a representative prevalence estimate.
"""
from __future__ import annotations
import json, shutil, subprocess, sys
from pathlib import Path
from ecwg import rank

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / 'data' / 'synthetic_cases'
DOMAINS = [
    'invoice_rounding', 'session_expiry', 'retry_backoff', 'cache_invalidation',
    'cursor_pagination', 'unicode_escaping', 'request_throttling', 'image_scaling',
    'search_deduplication', 'config_precedence', 'timezone_scheduling',
    'percentile_metrics', 'shipment_costs', 'stock_reservation',
    'upload_checksum', 'notification_batching',
]


def create_case(i: int, domain: str):
    case = FIX / f'case_{i+1:02d}'
    if case.exists():
        shutil.rmtree(case)
    for folder in ('lib', 'tests'):
        (case / folder).mkdir(parents=True)
        (case / folder / '__init__.py').write_text('', encoding='utf-8')
    deep = i < 12
    fname = f'apply_{domain}'
    issue = f'The {domain.replace("_", " ")} path returns the wrong numerical result under a regression scenario.'
    api = (f'from lib.engine_{i+1:02d} import calculate\n\n'
           f'def {fname}(value: int) -> int:\n'
           f'    """Apply {domain.replace("_", " ")} for this request."""\n'
           f'    return calculate(value){"" if deep else " - 1"}\n')
    engine = (f'def calculate(value: int) -> int:\n'
              f'    """Perform a low-level numerical operation."""\n'
              f'    return value + {1 if deep else 2}\n')
    legacy = (f'def {fname}_legacy(value: int) -> int:\n'
              f'    """Obsolete {domain.replace("_", " ")} utility. Do not call."""\n'
              f'    return value + 3\n')
    test_name = f'test_{domain}_regression'
    test = (f'from lib.{domain}_api import {fname}\n\n'
            f'def {test_name}():\n'
            f'    assert {fname}(3) == 5\n')
    (case / 'lib' / f'{domain}_api.py').write_text(api, encoding='utf-8')
    (case / 'lib' / f'engine_{i+1:02d}.py').write_text(engine, encoding='utf-8')
    (case / 'lib' / f'{domain}_legacy.py').write_text(legacy, encoding='utf-8')
    (case / 'tests' / f'test_{domain}.py').write_text(test, encoding='utf-8')
    target = f'lib.engine_{i+1:02d}.calculate' if deep else f'lib.{domain}_api.{fname}'
    bad_path = case / 'lib' / (f'engine_{i+1:02d}.py' if deep else f'{domain}_api.py')
    original = bad_path.read_text(encoding='utf-8')
    replacement = original.replace('return value + 1', 'return value + 2') if deep else original.replace('return calculate(value) - 1', 'return calculate(value)')
    def check():
        for cache in case.rglob("__pycache__"):
            shutil.rmtree(cache)
        return subprocess.run([sys.executable, '-c', f'from tests.test_{domain} import {test_name}; {test_name}()'],
                              cwd=case, capture_output=True, text=True, timeout=20).returncode
    # Confirm failing test and ground-truth correction; restore original afterwards.
    before = check()
    bad_path.write_text(replacement, encoding='utf-8')
    after = check()
    bad_path.write_text(original, encoding='utf-8')
    if before == 0 or after != 0:
        raise RuntimeError(f'Invalid fixture {domain}: failing={before}, fixed={after}')
    failing = f'tests.test_{domain}.{test_name}'
    bas = rank(case, issue, failing, 'lexical')
    wit = rank(case, issue, failing, 'witness')
    return {'id': f'case_{i+1:02d}', 'issue': issue, 'failing_test': failing,
            'fault_depth': 'implementation' if deep else 'entrypoint',
            'ground_truth_symbol': target, 'test_fails_before_fix': True,
            'test_passes_after_fix': True,
            'lexical_rank': next((j+1 for j, x in enumerate(bas) if x['symbol']==target), None),
            'witness_rank': next((j+1 for j, x in enumerate(wit) if x['symbol']==target), None),
            'lexical_top1': bas[0]['symbol'], 'witness_top1': wit[0]['symbol']}


def main():
    FIX.mkdir(exist_ok=True, parents=True)
    (ROOT / 'results').mkdir(exist_ok=True)
    rows = [create_case(i, domain) for i, domain in enumerate(DOMAINS)]
    def metrics(key):
        return {'top1_correct': sum(x[key] == 1 for x in rows),
                'top1_total': len(rows),
                'recall_at_2': sum(x[key] is not None and x[key] <= 2 for x in rows)}
    summary = {'dataset': '16 deliberately designed synthetic multi-file Python bugs',
               'composition': {'implementation_level': 12, 'entrypoint_level': 4},
               'baseline': 'Lexical symbol/docstring overlap + failing-test name',
               'method': 'Fixed-score test-conditioned AST call-graph routing',
               'lexical': metrics('lexical_rank'),
               'witnessgraph': metrics('witness_rank'),
               'notes': 'This is a biased synthetic stress test, not competition or real-world issue resolution performance.',
               'cases': rows}
    (ROOT / 'results' / 'pilot_results.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k != 'cases'}, indent=2))


if __name__ == '__main__':
    main()
