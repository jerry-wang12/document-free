---
name: teacher-grading-agent
description: Use this skill when the user asks for end-to-end grading assistance for a batch of student documents using a grading rubric and needs separated storage for rules, submissions, and outputs by date and run. It orchestrates rubric normalization, evidence-based scoring, and export to XLSX or HTML with review queue support.
---

# Teacher Grading Agent

Use this as the top-level workflow for local daily grading tasks.

## Input Contract

Required inputs:
- `date` in `YYYY-MM-DD`
- `rubric source` (YAML preferred; DOCX/PDF allowed)
- `submission directory` containing `.pdf`, `.docx`, `.xlsx`
- `output formats` (`xlsx`, `html`, or both)

## Storage Layout

Always keep datasets separated by date:
- `data/rules/<date>/`
- `data/submissions/<date>/`
- `data/outputs/<date>/<run-id>/`
- `data/runs/<date>/<run-id>/`

## Run Procedure

1. Build `run-id` as `run-YYYYMMDD-HHMMSS-<label>`.
2. If rubric is not YAML, invoke [rubric-builder](../rubric-builder/SKILL.md).
3. Invoke [evidence-grader](../evidence-grader/SKILL.md) for per-file evidence-based scoring.
4. Invoke [result-exporter](../result-exporter/SKILL.md) to generate outputs.
5. Create `manifest.yaml` in `data/runs/<date>/<run-id>/` and record all paths.

## Hard Rules

- Never output a score without evidence.
- Any item below confidence threshold must go to manual review queue.
- Never overwrite prior runs; always create a new run folder.

For output fields and checks, see [workflow.md](references/workflow.md).
