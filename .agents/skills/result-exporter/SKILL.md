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
- `report.html`: single-file summary dashboard (open directly in browser)

## Required summary metrics in `report.html`

- total files processed
- average score
- score distribution by band
- review-required count and ratio
- top recurring review reasons

## Language and presentation rules

- All teacher-facing labels and review reasons must be Chinese.
- Normalize common codes like `confidence<0.75` into readable Chinese.
- Keep `report.html` as a single file (no build step required).

## Recommended report generator

Use:

```bash
python3 references/generate_report_html.py --manifest <manifest.yaml>
```

Example:

```bash
python3 .agents/skills/result-exporter/references/generate_report_html.py \
  --manifest data/runs/2026-03-13/run-20260313-113251-class-a-writing/manifest.yaml
```

For suggested XLSX columns, see [export-columns.md](references/export-columns.md).
