# Scope, limitations and research integrity

**Implemented:** AST extraction of Python functions and simple call edges; test-conditioned ranking; static-path and source-hash certificates; reproducible hand-built synthetic pilot; optional local model *text* suggestion.

**Not implemented or evaluated:** Gemma 4 model inference in the current environment; GNN architecture or training; GPU/memory benchmarks; online inference; automatic patch application; automated real-world issue resolution; SWE-bench/Kaggle held-out evaluation; statistical claims about real repositories.

## Sources of bias

1. Synthetic pilot contains exactly 12 low-level implementation faults and four wrapper faults. The method's preference for graph terminal functions is purposely favored by this composition; it fails all four wrapper faults at top-1.
2. Function names and synthetic issue texts are simple and predictable. A larger held-out real corpus may behave differently.
3. Static AST calls miss reflection, monkey-patching, dynamic dispatch, class methods, alias resolution, nested functions, decorators, and many forms of relative imports.
4. Source-hash certificates verify that *specific code and paths* remain unchanged. They are not signed, cannot prove runtime causality, and can be regenerated after deliberate edits.
5. Neither code search/ranking nor an LLM draft is evidence that any bug was fixed. Only validation on independent held-out tests could support repair claims.
6. The generic Kaggle code-graph JSON adapter is schema-tolerant demonstration code, not an official competition integration.

## Follow-on experimental design

For a stronger paper, fix a real evaluation split before tuning, report top-k retrieval and patch-pass rates separately, measure performance across graph size/hop count, run edge permutation/node rename tests, and record compute/context/token budgets. Compare serialized edge lists vs graph-retrieved paths vs GNN-encoded representations using identical model checkpoints and evaluation hardware. Include a real-fault category breakdown and multiple seeds. Consult the original proposal mapping for RQ1/RQ2/RQ3.
