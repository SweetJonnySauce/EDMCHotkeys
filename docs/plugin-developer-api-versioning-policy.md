# Plugin Developer API Versioning and Changelog Policy

## Purpose
Define consistent rules for classifying and documenting API changes for plugin developers.

## Compatibility Labels
Apply one of these labels to each public symbol in API reference docs:

| Label | Meaning | Expectation |
| --- | --- | --- |
| `stable` | Backward compatibility expected across normal releases. | Breaking changes require explicit major-version-style communication and migration notes. |
| `experimental` | Contract may change with short notice. | Changes are allowed but must be called out clearly in release notes. |
| `deprecated` | Supported temporarily and scheduled for removal/replacement. | Must include replacement path and expected removal window. |

## Change Classification
Every API-affecting change must be tagged in docs/changelog as one of:

| Class | Definition | Typical examples |
| --- | --- | --- |
| `breaking` | Existing integrations can fail or require code changes. | removed symbol, signature change, stricter required args |
| `behavioral` | Signature unchanged but runtime behavior changes materially. | callback dispatch semantics adjusted |
| `additive` | New capabilities without breaking existing usage. | new optional field, new helper |
| `clarification` | No behavior change; docs accuracy/wording improvements only. | corrected return-value description |

## Changelog Requirements
For each `breaking`, `behavioral`, or `additive` API change:
- include an entry in `RELEASE_NOTES.md`
- include impacted symbol(s)
- include migration guidance when applicable
- include compatibility label changes where relevant

Recommended entry format:
1. `Type`: breaking/behavioral/additive/clarification
2. `API`: symbol name(s)
3. `Change`: concise summary
4. `Impact`: who is affected
5. `Migration`: exact action to take

## Deprecation Policy
Minimum requirements for deprecating a public API:
- mark symbol as `deprecated` in API reference
- provide replacement API and usage example
- add deprecation notice in release notes
- define expected removal target (release or date window)

Removal requirements:
- symbol remains documented until removal release ships
- removal release notes must include final migration guidance

## Documentation and Release Checklist Integration
For API-affecting PRs, reviewers must confirm:
1. API reference updated (or explicitly marked not applicable).
2. Integration guide updated when examples are impacted.
3. Troubleshooting updated when failure modes or logs change.
4. Release notes include required API change entry.
5. Compatibility labels and change class are present and correct.

Review workflow checklist:
- `docs/plugin-developer-api-review-checklist.md`

## Classification Consistency Notes
When ambiguous between `behavioral` and `breaking`:
- use `breaking` if existing plugin code likely needs modification
- use `behavioral` if code compiles/runs but observed behavior changes

When ambiguous between `additive` and `clarification`:
- use `additive` if runtime capabilities changed
- use `clarification` if only documentation wording changed
