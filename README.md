# document-free

一个面向老师日常文档工作的本地 Agent 项目：
- 读取学生材料（PDF / DOCX / XLSX）
- 按评分规则进行 AI 辅助评分
- 输出结果（`result.xlsx` / `report.html` / `review_queue.xlsx`）
- 全流程按日期与 run 隔离，便于追溯

## 环境安装

- 本地环境配置说明：`docs/ENV_SETUP.md`

## 1. 项目定位

本项目是“老师本地 + AI 助手协作”模式，不是传统 Web 系统。
你可以用国内可用的工具（如 Qwen Coding Plan、Trae）按本文档流程完成批处理。

## 2. 目录结构

```text
document-free/
  .agents/skills/
    docx/
    xlsx/
    pdf/
    pptx/
    teacher-grading-agent/
    rubric-builder/
    evidence-grader/
    result-exporter/

  data/
    rules/
      YYYY-MM-DD/
    submissions/
      YYYY-MM-DD/
    outputs/
      YYYY-MM-DD/
        <run-id>/
    runs/
      YYYY-MM-DD/
        <run-id>/
```

## 3. 已安装技能

### 通用文档技能
- `docx`
- `xlsx`
- `pdf`
- `pptx`

### 本项目工作流技能
- `teacher-grading-agent`：总入口，编排全流程
- `rubric-builder`：将规则文档规范化为 YAML rubric
- `evidence-grader`：按 rubric 逐文件评分并附证据/置信度
- `result-exporter`：导出 xlsx/html 与复核队列

## 4. 一次评分任务（推荐流程）

1. 选择日期目录（例如 `2026-03-13`）。
2. 放入评分规则：
   - 推荐 YAML：`data/rules/2026-03-13/rubric-xxx.yaml`
   - 如是 DOCX/PDF，可先让 agent 用 `rubric-builder` 转成 YAML。
3. 放入待评分材料：
   - `data/submissions/2026-03-13/<班级或任务名>/`
4. 让 agent 执行评分：
   - 生成新的 `run-id`
   - 写入 `data/runs/<date>/<run-id>/`（manifest、raw、logs）
   - 写入 `data/outputs/<date>/<run-id>/`（xlsx/html）

## 5. 常用提示词模板（直接复制给 Agent）

### 5.1 从规则文档生成 rubric

```text
请使用 rubric-builder：
读取 data/rules/2026-03-13/ 里的规则文档，输出标准化 YAML 到
data/rules/2026-03-13/rubric-writing-v1.yaml。
要求校验权重和分值总和，并写明 confidence_threshold。
```

### 5.2 批量评分并导出结果

```text
请使用 teacher-grading-agent：
按 data/rules/2026-03-13/rubric-demo.yaml
评分 data/submissions/2026-03-13/ 下全部文件。
输出 result.xlsx、review_queue.xlsx、report.html。
低于阈值的条目进入人工复核队列。
```

### 5.3 只做导出

```text
请使用 result-exporter：
将 data/runs/2026-03-13/<run-id>/grading_raw.jsonl
导出到 data/outputs/2026-03-13/<run-id>/。
```

### 5.4 重生成可视化 `report.html`（Vue + Tailwind 单文件）

```bash
python3 .agents/skills/result-exporter/references/generate_report_html.py \
  --manifest data/runs/2026-03-13/<run-id>/manifest.yaml
```

## 6. 命名约定

- 日期目录：`YYYY-MM-DD`
- run-id：`run-YYYYMMDD-HHMMSS-<label>`

示例：`run-20260313-143000-class1-writing`

## 7. 结果解释与复核

`review_queue.xlsx` 中通常包含以下情况：
- 置信度低于阈值
- 维度证据不完整
- 原文解析异常但仍给出部分评分

建议老师优先人工复核这些条目。

## 8. 模板文件

- `data/rules/rubric.template.yaml`
- `data/rules/2026-03-13/rubric-demo.yaml`
- `data/runs/manifest.template.yaml`
- `data/runs/2026-03-13/run-20260313-120000-demo/manifest.yaml`

## 9. 注意事项

- 评分结论应始终附证据片段（evidence）。
- 结果文件建议每次写入新 run 目录，避免覆盖。
- 更新流程后建议重启你使用的 AI 工具或编辑器插件。
