# Plugin Developer API Docs Review Checklist

Use this checklist for PRs that change the plugin developer API surface or behavior.

Related policy:
- `docs/plugin-developer-api-versioning-policy.md`

## Applicability
Apply this checklist when a PR changes any of:
- exported API symbols in `__init__.__all__`
- public wrapper signatures in `load.py`
- `Action` or `Binding` dataclass contract fields/defaults
- runtime behavior that changes developer-observable API semantics

If none apply, reviewers may mark this checklist as not applicable.

## Author Checklist
1. API reference updated if symbol/signature/semantics changed.
2. Integration guide updated if examples or workflow changed.
3. Troubleshooting updated if failure modes/log patterns changed.
4. Release notes updated for `breaking`, `behavioral`, or `additive` changes.
5. Compatibility label and change classification applied per policy.
6. Docs checks pass locally:
- `python scripts/check_docs_links.py`
- `python scripts/check_plugin_api_docs.py`
- `python scripts/check_doc_snippets.py`

## Reviewer Rubric (Yes/No)
- `Yes/No`: Does the PR modify API surface or observable API behavior?
- `Yes/No`: Are all affected docs updated in the same PR?
- `Yes/No`: Are changelog and classification entries consistent with policy?
- `Yes/No`: Do docs checks pass or have justified exceptions?
- `Yes/No`: Are migration notes present for any `breaking` change?

A PR should not merge if any required `Yes` answer is `No`.
