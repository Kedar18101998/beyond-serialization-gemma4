"""`ecwg` command line interface — offline unless `propose` explicitly used."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from .certificates import make_certificate, verify_certificate
from .core import analyze, rank
from .local_model import DEFAULT_ENDPOINT, propose_patch


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog='ecwg', description='Evidence-Certified Witness Graphs research prototype')
    commands = p.add_subparsers(dest='command', required=True)
    graph = commands.add_parser('graph', help='Summarize a repository static call graph')
    graph.add_argument('--root', required=True, type=Path)
    localize = commands.add_parser('rank', help='Rank likely source locations')
    localize.add_argument('--root', required=True, type=Path)
    localize.add_argument('--issue', required=True)
    localize.add_argument('--failing-test', required=True)
    localize.add_argument('--method', choices=['lexical', 'witness'], default='witness')
    localize.add_argument('--top-k', type=int, default=5)
    cert = commands.add_parser('certificate', help='Produce static path evidence as JSON')
    cert.add_argument('--root', required=True, type=Path)
    cert.add_argument('--failing-test', required=True)
    cert.add_argument('--target', required=True)
    check = commands.add_parser('verify', help='Recheck static path evidence against current source')
    check.add_argument('--root', required=True, type=Path)
    check.add_argument('--certificate', required=True, type=Path)
    propose = commands.add_parser('propose', help='Ask a locally running Ollama model to draft a diff (never applies it)')
    propose.add_argument('--root', required=True, type=Path)
    propose.add_argument('--issue', required=True)
    propose.add_argument('--failing-test', required=True)
    propose.add_argument('--model', required=True, help='Already installed model identifier, e.g. a local Gemma 4 tag')
    propose.add_argument('--endpoint', default=DEFAULT_ENDPOINT)
    propose.add_argument('--output', type=Path)
    patch = commands.add_parser('check-patch', help='Non-mutating git apply --check for a locally saved patch')
    patch.add_argument('--root', required=True, type=Path)
    patch.add_argument('--patch', required=True, type=Path)
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.command == 'graph':
        nodes, edges = analyze(args.root)
        print(json.dumps({'functions': len(nodes), 'calls': sum(map(len, edges.values())),
                          'test_functions': sum(v['is_test'] for v in nodes.values())}, indent=2))
    elif args.command == 'rank':
        if args.top_k < 1:
            raise ValueError('--top-k must be positive')
        print(json.dumps(rank(args.root, args.issue, args.failing_test, args.method)[:args.top_k], indent=2))
    elif args.command == 'certificate':
        print(json.dumps(make_certificate(args.root, args.failing_test, args.target), indent=2))
    elif args.command == 'verify':
        status, issues = verify_certificate(args.root, json.loads(args.certificate.read_text(encoding='utf-8')))
        print(json.dumps({'valid': status, 'errors': issues}, indent=2))
        return 0 if status else 1
    elif args.command == 'propose':
        result = propose_patch(args.root, args.issue, args.failing_test, model=args.model, endpoint=args.endpoint)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(result + '\n', encoding='utf-8')
            print(f'Wrote UNVERIFIED model suggestion to {args.output}. Review before applying.')
        else:
            print(result)
    elif args.command == 'check-patch':
        root = args.root.resolve()
        if not root.is_dir():
            raise ValueError('Repository directory does not exist')
        proc = subprocess.run(['git', '-C', str(root), 'apply', '--check', '-'],
                              input=args.patch.read_bytes(), capture_output=True, timeout=25)
        print(json.dumps({'can_apply': proc.returncode == 0,
                          'stderr': proc.stderr.decode('utf-8', errors='replace')}, indent=2))
        return 0 if proc.returncode == 0 else 1
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print(f'ecwg: {exc}', file=sys.stderr)
        sys.exit(2)
