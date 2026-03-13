# Workflow Reference

## Recommended columns for `result.xlsx`

- `student_id`
- `student_name`
- `source_file`
- `total_score`
- `dimension_scores_json`
- `evidence_snippets`
- `confidence`
- `review_required`
- `review_reason`

## Review queue rules

Add an item to `review_queue.xlsx` when any condition is true:
- `confidence < rubric.policy.confidence_threshold`
- Missing evidence for any scored dimension
- File parse failed but a partial score was still produced

## Run artifacts

- `manifest.yaml`
- `grading_raw.jsonl`
- `logs.txt`
