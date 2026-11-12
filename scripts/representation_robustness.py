#!/usr/bin/env python3
"""Small, reproducible robustness and certificate sanity checks.

Important: this is a deterministic diagnostic over synthetic repos, not an LLM,
GNN, Kaggle held-out benchmark, or real bug fix evaluation.
"""
from __future__ import annotations
import json, shutil, tempfile
from collections import deque
from pathlib import Path
from run_pilot import main as generate_pilot
from ecwg import analyze, rank

HERE = Path(__file__).resolve().parents[1]


def find_path(edges, start, goal):
    if start == goal: return [start]
    q = deque([(start, [start])]); seen = {start}
    while q:
        at, p = q.popleft()
        for nxt in sorted(edges.get(at, ())):
            if nxt in seen: continue
            if nxt == goal: return p + [nxt]
            seen.add(nxt); q.append((nxt, p + [nxt]))
    return None


def certificate_valid(nodes, edges, path):
    return bool(path and len(path) >= 2 and all(n in nodes for n in path)
                and all(v in edges.get(u, ()) for u, v in zip(path, path[1:])))


def rename_low_level_calculate(repo):
    # Semantics-preserving source rewrite: update one imported function consistently.
    for path in repo.rglob('*.py'):
        text = path.read_text(encoding='utf-8')
        text = text.replace('calculate', 'compute_value')
        path.write_text(text, encoding='utf-8')


def evaluate():
    generate_pilot()
    base = json.loads((HERE / 'results' / 'pilot_results.json').read_text(encoding='utf-8'))
    outcomes = []
    with tempfile.TemporaryDirectory(prefix='witness_graph_') as temporary:
        temp = Path(temporary)
        for rec in base['cases']:
            original = HERE / 'data' / 'synthetic_cases' / rec['id']
            case = temp / rec['id']; shutil.copytree(original, case)
            issue, failing, target = rec['issue'], rec['failing_test'], rec['ground_truth_symbol']
            nodes, edges = analyze(case)
            valid = find_path(edges, failing, target)
            # Tamper with the last step: a real node is substituted, but the call edge is absent.
            legacy = next(name for name in nodes if name.endswith('_legacy'))
            fake = valid[:-1] + [legacy] if valid else [failing, legacy]
            baseline_rank = rec['witness_rank']
            # Ablation removes the failing-test symbol; this disables witness reachability.
            witness_blind = rank(case, issue, '', method='witness')
            blind_position = next((j+1 for j, r in enumerate(witness_blind)
                                   if r['symbol'] == target), None)
            # Identifier perturbation - target and call sites renamed consistently.
            rename_low_level_calculate(case)
            renamed_target = target.replace('calculate', 'compute_value')
            renamed = rank(case, issue, failing, method='witness')
            renamed_position = next((j+1 for j, r in enumerate(renamed)
                                     if r['symbol'] == renamed_target), None)
            outcomes.append({
                'id': rec['id'], 'depth': rec['fault_depth'],
                'original_witness_rank': baseline_rank,
                'no_test_witness_rank': blind_position,
                'renamed_witness_rank': renamed_position,
                'genuine_certificate_valid': certificate_valid(nodes, edges, valid),
                'tampered_certificate_rejected': not certificate_valid(nodes, edges, fake),
                'certificate_length_edges': len(valid)-1 if valid else None,
            })
    top1 = lambda key: sum(r[key] == 1 for r in outcomes)
    summary = {
        'experimental_scope': '16 constructed Python fixtures; no LLM, GNN, or Kaggle scoring',
        'synthetic_case_count': len(outcomes),
        'baseline_lexical_top1': base['lexical']['top1_correct'],
        'baseline_witness_top1': top1('original_witness_rank'),
        'witness_without_test_id_top1': top1('no_test_witness_rank'),
        'witness_after_consistent_identifier_rename_top1': top1('renamed_witness_rank'),
        'genuine_paths_validated': sum(r['genuine_certificate_valid'] for r in outcomes),
        'tampered_paths_rejected': sum(r['tampered_certificate_rejected'] for r in outcomes),
        'cautions': ['Synthetic fixture distribution selected deliberately',
                     'Certificate check verifies graph edges, not causal influence',
                     'Renaming test rewrites exactly the low-level calculate symbol',
                     'No learned GNN or Gemma model was tested'],
        'cases': outcomes,
    }
    (HERE / 'results' / 'proposal_diagnostics.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in summary.items() if k != 'cases'}, indent=2))

if __name__ == '__main__':
    evaluate()
