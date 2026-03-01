# Plugin Developer API Reference Strategy Decision

## Context
`EDMCHotkeys` exposes a Python module integration API. We need an API reference that is accurate, readable, and resilient to drift as code evolves.

## Decision
Use a **hybrid strategy**:
- generated symbol/signature inventory from code
- manually curated behavior semantics and examples in markdown

## Alternatives Considered

### Option A: Manual-only reference
Pros:
- lowest implementation complexity
- flexible writing quality

Cons:
- highest drift risk for signatures
- reviewers must manually verify every API change against docs

### Option B: Fully generated reference
Pros:
- lowest signature drift risk
- deterministic output from source

Cons:
- poor readability for nuanced behavior/caveats
- harder to present integration guidance cleanly

### Option C: Hybrid (Chosen)
Pros:
- generated accuracy where drift hurts most (symbol/signature tables)
- curated semantics remain readable for plugin developers
- manageable implementation complexity

Cons:
- requires ownership discipline for both generated and curated portions

## Rationale
The plugin API surface is small enough for readable manual semantics, but critical enough to enforce signature accuracy mechanically. Hybrid provides the best cost/benefit tradeoff.

## Implementation Contract

### Inputs
- `__init__.__all__` exported symbols
- callable signatures resolved from module attributes
- dataclass field definitions for `Action` and `Binding`

### Outputs
- generated artifact for drift checking (machine-readable snapshot under `docs/` or `scripts/`-managed output)
- generated markdown symbol/signature table consumed by API reference

### Invariants
- every exported symbol in `__all__` appears in generated inventory
- generated signatures match importable runtime symbols
- API reference includes all generated symbols

### CI Integration Target (Phase 4)
- add a docs drift script (for example `scripts/check_plugin_api_docs.py`)
- fail CI on missing or mismatched symbols/signatures

## Drift Failure Behavior
- missing symbol in docs: fail check
- extra stale symbol in docs: fail check
- signature mismatch: fail check
- non-critical prose mismatch: warning/manual review

## Paper Test Scenarios
1. Add new exported function:
- expected outcome: generator includes symbol; drift check fails until reference includes it.
2. Change `invoke_action` parameter defaults:
- expected outcome: signature diff detected; drift check fails until docs are updated.
3. Rename an exported dataclass field:
- expected outcome: generated dataclass shape changes; docs mismatch detected.

## Rollback Strategy
If generator maintenance cost becomes disproportionate:
- keep generated inventory only for CI drift checking
- maintain human-authored markdown sections manually
- defer table autogeneration while preserving mechanical API parity checks
