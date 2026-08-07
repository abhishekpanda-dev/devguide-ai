# 0005: Persist bounded repository structure intelligence

## Status

Accepted

## Decision

After parsing and deterministic findings, extract repository-local Python, JavaScript, and
TypeScript dependency evidence without executing code. Persist one readiness record per analysis,
one metrics/entry-point record per existing `repository_files` row, and validated file-to-file
edges. Do not duplicate file contents.

Python imports use the standard-library AST. JavaScript and TypeScript use bounded static syntax
inspection for literal ES imports, reexports, and `require` calls. Only relative JavaScript paths
and Python modules that resolve to persisted files create edges. Dynamic expressions and external
packages create no edge.

Python resolution checks `module.py` before `module/__init__.py`. JavaScript/TypeScript resolution
checks an explicit path, then `.ts`, `.tsx`, `.js`, `.jsx`, `.mjs`, `.cjs`, followed by equivalent
`index` files. Entry points are probable evidence from `__main__.py`, exact main guards,
`package.json` main/module/bin fields, or a conventional `src/main.*` backed by Vite/React package
metadata.

## Consequences

Inbound, outbound, and total edge counts are deterministic static coupling signals, not judgments
of quality or proof of runtime behavior. A zero-edge readiness row distinguishes completed empty
analysis from unavailable structure. The configured edge cap bounds storage and analysis time.
Unresolved imports are omitted rather than guessed. The structure service is an extension point for
future grounded Q&A retrieval; this milestone does not inject graph data into model prompts.
