#!/usr/bin/env python3
"""Offline query-to-code-graph candidate reranker for Kaggle-like node/edge JSON.

Adapter is schema-tolerant but necessarily experimental: we do not bundle the
competition's 23+ GB dataset. A returned list is not evidence of issue repair.
No task patches, test patches, or hidden labels are read or used.
"""
from __future__ import annotations
import argparse, json, math, re
from collections import defaultdict
from pathlib import Path


def toks(s):
    s = re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', str(s))
    return set(re.findall(r'[a-z0-9]+', s.lower().replace('_', ' '))) - {'the','and','for','from','with','that','this','test','def','class','return','in','is','of','to','on','a','an'}


def normalize_graph(data):
    if isinstance(data, list):
        raise ValueError('Expected graph object with nodes and links/edges, not a list.')
    obj = data.get('graph', data)
    nodes_raw = obj.get('nodes', obj.get('vertices', []))
    if isinstance(nodes_raw, dict):
        nodes_raw = [{'id': k, **(v if isinstance(v, dict) else {'text': str(v)})} for k,v in nodes_raw.items()]
    nodes = {}
    for node in nodes_raw:
        if isinstance(node, str): node = {'id': node, 'name': node}
        key = str(node.get('id', node.get('name', '')))
        if key:
            nodes[key] = {'name': str(node.get('name', key)), 'text': str(node.get('text', node.get('code', ''))),
                          'type': str(node.get('type', node.get('kind', '')))}
    edges = defaultdict(dict)
    for ed in obj.get('edges', obj.get('links', [])):
        a, b = str(ed.get('source', '')), str(ed.get('target', ''))
        if a not in nodes or b not in nodes or a == b: continue
        etype = str(ed.get('type', ed.get('relation', ''))).lower()
        weight = 1.0 if 'call' in etype else 0.7 if any(w in etype for w in ('import','reference','usage')) else 0.45
        edges[a][b] = max(edges[a].get(b, 0.0), weight)
        edges[b][a] = max(edges[b].get(a, 0.0), weight)
    return nodes, edges


def retrieve(data, issue, k=12, alpha=0.6, hops=3):
    nodes, edges = normalize_graph(data)
    if not nodes: return []
    query = toks(issue)
    raw = {}
    for nodeid, n in nodes.items():
        symbols = toks(n['name'])
        # Names are intentional anchors; short code/docstring can add weak evidence.
        raw[nodeid] = 2.0 * len(query & symbols) / math.sqrt(1 + len(symbols)) + 0.2 * len(query & toks(n['text'][:300]))
    maxraw = max(raw.values(), default=0) or 1
    lexical = {n: s / maxraw for n, s in raw.items()}
    # Diffusion is untrained, typed-edge-weighted, and bounded to 3 iterations.
    strength = lexical.copy()
    for _ in range(max(0, int(hops))):
        newer = {}
        for n in nodes:
            nbrs = edges.get(n, {})
            denom = sum(nbrs.values()) or 1
            neighbor_signal = sum(w * strength[other] for other, w in nbrs.items()) / denom
            newer[n] = alpha * lexical[n] + (1-alpha) * neighbor_signal
        strength = newer
    ranked = sorted(nodes, key=lambda n: (-strength[n], n))[:k]
    return [{'node': n, 'name': nodes[n]['name'], 'type': nodes[n]['type'],
             'lexical': round(lexical[n], 5), 'graph_score': round(strength[n], 5),
             'neighbors': list(edges.get(n, {}))[:5], 'excerpt': nodes[n]['text'][:250]} for n in ranked]


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--graph', type=Path, required=True, help='Kaggle-style JSON with nodes and edges')
    p.add_argument('--issue', required=True)
    p.add_argument('--top-k', type=int, default=12)
    args = p.parse_args()
    print(json.dumps(retrieve(json.loads(args.graph.read_text()), args.issue, args.top_k), indent=2))

if __name__ == '__main__': main()
