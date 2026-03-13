---
name: result-exporter
description: Use this skill when grading raw outputs exist in JSONL and the task is to generate teacher-friendly deliverables such as result.xlsx, review_queue.xlsx, and report.html in a date-partitioned run output folder.
---

# Result Exporter

Convert raw grading artifacts into teacher-facing files.

## Input

- `data/runs/<date>/<run-id>/grading_raw.jsonl`
- `data/runs/<date>/<run-id>/manifest.yaml`

## Output directory

- `data/outputs/<date>/<run-id>/`

## Required artifacts

- `result.xlsx`: full scoring table
- `review_queue.xlsx`: low-confidence or incomplete-evidence items
- `report.html`: summary metrics and review suggestions

## Required summary metrics in `report.html`

- total files processed
- average score
- score distribution by band
- review-required count and ratio
- top recurring review reasons

For suggested XLSX columns, see [export-columns.md](references/export-columns.md).
