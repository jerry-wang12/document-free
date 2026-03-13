---
name: rubric-builder
description: Use this skill when grading rules exist in natural language documents (DOCX, PDF, or notes) and must be converted into a normalized rubric YAML with dimensions, weights, score ranges, and confidence and review policies.
---

# Rubric Builder

Normalize grading rules into a single YAML rubric for stable scoring.

## Output

Write normalized rubric to:
- `data/rules/<date>/rubric-<task>-v<version>.yaml`

## Required schema

- `rubric.id`
- `rubric.title`
- `rubric.version`
- `rubric.total_score`
- `rubric.dimensions[]` with `key`, `name`, `weight`, `max_score`
- `policy.confidence_threshold`
- `policy.require_evidence`

## Procedure

1. Read source rule text from DOCX, PDF, or plain text.
2. Extract dimensions, weights, and score boundaries.
3. Resolve ambiguity explicitly and write unresolved notes to run logs.
4. Ensure `sum(max_score) == total_score`.
5. Ensure `sum(weight) == 1.0`.

For an example, see [rubric-schema-example.yaml](references/rubric-schema-example.yaml).
