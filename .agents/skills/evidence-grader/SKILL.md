---
name: evidence-grader
description: Use this skill when a normalized rubric and a batch of student documents are available and the task is to produce per-document scoring with evidence snippets, reasons, and confidence values for manual review gating.
---

# Evidence Grader

Score student files with explicit evidence and confidence.

## Input

- Rubric YAML in `data/rules/<date>/`
- Student files in `data/submissions/<date>/...`

## Output

Write line-delimited JSON to:
- `data/runs/<date>/<run-id>/grading_raw.jsonl`

Each JSON line must include:
- `source_file`
- `student_id` (if available)
- `scores[]` with `dimension_key`, `score`, `reason`, `evidence`, `confidence`
- `total_score`
- `confidence`
- `review_required`
- `review_reason`

## Hard rules

- Evidence must cite source content segments.
- `reason` and `review_reason` should be Chinese for teacher readability.
- If no reliable evidence exists, set low confidence and flag for review.
- Never fabricate student identity fields.

For a sample output line, see [output-jsonl-example.md](references/output-jsonl-example.md).
