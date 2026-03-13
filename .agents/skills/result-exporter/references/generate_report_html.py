#!/usr/bin/env python3
import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

import yaml


def find_repo_root_from_manifest(manifest_path: Path) -> Path:
    cur = manifest_path.resolve()
    while cur.parent != cur and cur.name != "data":
        cur = cur.parent
    if cur.name == "data":
        return cur.parent
    return manifest_path.parent


def read_yaml(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def read_jsonl(path: Path):
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def mostly_ascii(text: str) -> bool:
    visible = [c for c in text if not c.isspace()]
    if not visible:
        return False
    ascii_count = sum(1 for c in visible if ord(c) < 128)
    return (ascii_count / len(visible)) >= 0.7


def normalize_review_reason(reason: str, threshold: float) -> str:
    if not reason:
        return "无"

    raw = reason.strip()
    lowered = raw.lower()

    if lowered.startswith("confidence<"):
        return f"置信度低于阈值（{threshold:.2f}）"
    if "missing evidence" in lowered:
        return "关键维度缺少证据片段"
    if "parser failed" in lowered or "parse failed" in lowered:
        return "文档解析异常，需人工核查"
    if "incomplete" in lowered:
        return "信息不完整，需人工核查"

    if mostly_ascii(raw):
        return f"需人工复核（原始代码：{raw}）"
    return raw


def normalize_dimension_reason(reason: str) -> str:
    if not reason:
        return "未提供评分说明。"
    if mostly_ascii(reason):
        return f"评分说明（原文）：{reason}"
    return reason


def score_bands(total_score_max: float):
    return [
        {
            "key": "needs_improvement",
            "label": "待提升",
            "min": 0.0,
            "max": round(total_score_max * 0.60, 2),
            "count": 0,
        },
        {
            "key": "pass",
            "label": "达标",
            "min": round(total_score_max * 0.60, 2),
            "max": round(total_score_max * 0.75, 2),
            "count": 0,
        },
        {
            "key": "good",
            "label": "良好",
            "min": round(total_score_max * 0.75, 2),
            "max": round(total_score_max * 0.90, 2),
            "count": 0,
        },
        {
            "key": "excellent",
            "label": "优秀",
            "min": round(total_score_max * 0.90, 2),
            "max": round(total_score_max, 2),
            "count": 0,
        },
    ]


def count_bands(items, bands, total_score_max: float):
    for item in items:
        score = float(item.get("total_score", 0.0))
        ratio = 0.0 if total_score_max <= 0 else max(0.0, min(1.0, score / total_score_max))
        if ratio < 0.60:
            bands[0]["count"] += 1
        elif ratio < 0.75:
            bands[1]["count"] += 1
        elif ratio < 0.90:
            bands[2]["count"] += 1
        else:
            bands[3]["count"] += 1
    return bands


def build_payload(manifest_path: Path, raw_path: Path):
    manifest = read_yaml(manifest_path)
    rows = read_jsonl(raw_path)

    repo_root = find_repo_root_from_manifest(manifest_path)
    rubric_path = Path(manifest.get("rubric_path", ""))
    if not rubric_path.is_absolute():
        rubric_path = repo_root / rubric_path
        rubric_path = rubric_path.resolve()

    rubric = read_yaml(rubric_path) if rubric_path.exists() else {}
    rubric_block = rubric.get("rubric", {})
    dimensions = rubric_block.get("dimensions", [])
    dim_name_map = {d.get("key"): d.get("name", d.get("key")) for d in dimensions}
    total_score_max = float(rubric_block.get("total_score", 100))

    threshold = float(manifest.get("policy", {}).get("confidence_threshold", 0.75))
    total_files = len(rows)
    avg_score = round(sum(float(r.get("total_score", 0.0)) for r in rows) / total_files, 2) if total_files else 0.0
    avg_conf = round(sum(float(r.get("confidence", 0.0)) for r in rows) / total_files, 3) if total_files else 0.0

    review_rows = [r for r in rows if bool(r.get("review_required"))]
    review_count = len(review_rows)
    review_ratio = round((review_count / total_files) * 100, 2) if total_files else 0.0

    reason_counter = Counter()
    dimension_values = defaultdict(list)
    table_rows = []

    for r in rows:
        review_reason = normalize_review_reason(r.get("review_reason", ""), threshold)
        if r.get("review_required"):
            reason_counter[review_reason] += 1

        dim_scores = []
        for s in r.get("scores", []):
            dim_key = s.get("dimension_key", "")
            dim_name = dim_name_map.get(dim_key, dim_key)
            score = float(s.get("score", 0.0))
            dimension_values[dim_name].append(score)
            dim_scores.append(
                {
                    "dimension_key": dim_key,
                    "dimension_name": dim_name,
                    "score": round(score, 2),
                    "reason": normalize_dimension_reason(s.get("reason", "")),
                    "evidence": s.get("evidence", ""),
                    "confidence": float(s.get("confidence", 0.0)),
                }
            )

        table_rows.append(
            {
                "student_id": r.get("student_id", ""),
                "source_file": r.get("source_file", ""),
                "total_score": round(float(r.get("total_score", 0.0)), 2),
                "confidence": round(float(r.get("confidence", 0.0)), 3),
                "review_required": bool(r.get("review_required")),
                "review_reason": review_reason,
                "scores": dim_scores,
            }
        )

    dim_avgs = [
        {"name": name, "avg_score": round(sum(vals) / len(vals), 2), "count": len(vals)}
        for name, vals in dimension_values.items()
        if vals
    ]
    dim_avgs.sort(key=lambda x: x["name"])

    bands = count_bands(rows, score_bands(total_score_max), total_score_max)
    top_reasons = [{"reason": k, "count": v} for k, v in reason_counter.most_common(10)]

    payload = {
        "meta": {
            "run_id": manifest.get("run_id", ""),
            "date": manifest.get("date", ""),
            "timezone": manifest.get("timezone", "Asia/Shanghai"),
            "rubric_path": manifest.get("rubric_path", ""),
            "submission_dir": manifest.get("submission_dir", ""),
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
        "summary": {
            "total_files": total_files,
            "total_score_max": total_score_max,
            "avg_score": avg_score,
            "avg_confidence": avg_conf,
            "review_count": review_count,
            "review_ratio": review_ratio,
            "confidence_threshold": threshold,
        },
        "bands": bands,
        "review_reasons": top_reasons,
        "dimension_averages": dim_avgs,
        "rows": table_rows,
    }
    return payload


def render_html(payload: dict) -> str:
    data_json = (
        json.dumps(payload, ensure_ascii=False)
        .replace("</", "<\\/")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )
    title = f"{payload['meta'].get('run_id', '')} - 评分报告"
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{title}</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = {{
      theme: {{
        extend: {{
          fontFamily: {{
            sans: ['\\"Noto Sans SC\\"', '\\"PingFang SC\\"', '\\"Microsoft YaHei\\"', 'sans-serif'],
            title: ['\\"ZCOOL XiaoWei\\"', 'serif']
          }},
          colors: {{
            ink: '#0f172a',
            paper: '#f8fafc',
            accent: '#0f766e',
            warm: '#f59e0b',
            alert: '#dc2626'
          }},
          boxShadow: {{
            glow: '0 10px 30px -10px rgba(15,118,110,0.35)'
          }}
        }}
      }}
    }};
  </script>
  <script src="https://unpkg.com/vue@3/dist/vue.global.prod.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
  <style>
    body {{
      margin: 0;
      background: #f8fafc;
      color: #0f172a;
      font-family: "Noto Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif;
    }}
    .fallback-wrap {{
      max-width: 1200px;
      margin: 0 auto;
      padding: 24px;
    }}
    .fallback-card {{
      background: #fff;
      border: 1px solid #e2e8f0;
      border-radius: 14px;
      padding: 16px;
      margin-top: 12px;
    }}
    .fallback-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 12px;
      margin-top: 12px;
    }}
    .fallback-table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 14px;
      margin-top: 10px;
    }}
    .fallback-table th, .fallback-table td {{
      border: 1px solid #e2e8f0;
      padding: 8px 10px;
      text-align: left;
      vertical-align: top;
    }}
    .fallback-table th {{
      background: #f1f5f9;
    }}
    .fallback-badge {{
      display: inline-block;
      padding: 2px 8px;
      border-radius: 999px;
      font-size: 12px;
    }}
    .ok {{
      background: #dcfce7;
      color: #166534;
    }}
    .warn {{
      background: #fee2e2;
      color: #991b1b;
    }}
    .bar-row {{
      margin: 8px 0;
      font-size: 14px;
    }}
    .bar-track {{
      height: 10px;
      background: #e2e8f0;
      border-radius: 999px;
      overflow: hidden;
      margin-top: 4px;
    }}
    .bar-fill {{
      height: 10px;
      background: linear-gradient(90deg, #0f766e, #0ea5e9);
    }}
  </style>
</head>
<body class="bg-paper text-ink min-h-screen">
  <div id="app" class="max-w-7xl mx-auto px-4 py-8 md:px-8 md:py-10">
    <header class="rounded-2xl p-6 md:p-8 bg-gradient-to-r from-teal-700 via-cyan-700 to-sky-700 text-white shadow-glow">
      <div class="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <p class="uppercase tracking-[0.25em] text-xs opacity-90">AI Grading Workspace</p>
          <h1 class="font-title text-4xl md:text-5xl mt-2">评分报告</h1>
          <p class="mt-3 text-sm md:text-base opacity-90">运行批次：{{{{ meta.run_id }}}}</p>
        </div>
        <div class="text-sm md:text-right space-y-1">
          <p><span class="opacity-80">日期</span>：{{{{ meta.date }}}}</p>
          <p><span class="opacity-80">规则文件</span>：{{{{ meta.rubric_path }}}}</p>
          <p><span class="opacity-80">生成时间</span>：{{{{ meta.generated_at }}}}</p>
        </div>
      </div>
    </header>

    <section class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4 mt-6">
      <article class="rounded-2xl bg-white p-5 shadow-sm border border-slate-100">
        <p class="text-slate-500 text-sm">总文件数</p>
        <p class="text-3xl font-semibold mt-2">{{{{ summary.total_files }}}}</p>
      </article>
      <article class="rounded-2xl bg-white p-5 shadow-sm border border-slate-100">
        <p class="text-slate-500 text-sm">平均分</p>
        <p class="text-3xl font-semibold mt-2">{{{{ summary.avg_score }}}} / {{{{ summary.total_score_max }}}}</p>
      </article>
      <article class="rounded-2xl bg-white p-5 shadow-sm border border-slate-100">
        <p class="text-slate-500 text-sm">平均置信度</p>
        <p class="text-3xl font-semibold mt-2">{{{{ summary.avg_confidence }}}}</p>
      </article>
      <article class="rounded-2xl bg-white p-5 shadow-sm border border-slate-100">
        <p class="text-slate-500 text-sm">需复核</p>
        <p class="text-3xl font-semibold mt-2 text-alert">{{{{ summary.review_count }}}} <span class="text-lg text-slate-500">({{{{ summary.review_ratio }}}}%)</span></p>
      </article>
    </section>

    <section class="grid grid-cols-1 xl:grid-cols-3 gap-4 mt-6">
      <article class="rounded-2xl bg-white p-5 border border-slate-100 shadow-sm xl:col-span-2">
        <h2 class="text-lg font-semibold">分数段分布</h2>
        <canvas id="bandChart" class="mt-4 h-64"></canvas>
      </article>
      <article class="rounded-2xl bg-white p-5 border border-slate-100 shadow-sm">
        <h2 class="text-lg font-semibold">复核原因占比</h2>
        <canvas id="reasonChart" class="mt-4 h-64"></canvas>
      </article>
    </section>

    <section class="mt-6 rounded-2xl bg-white p-5 border border-slate-100 shadow-sm">
      <h2 class="text-lg font-semibold">维度均分</h2>
      <canvas id="dimensionChart" class="mt-4 h-64"></canvas>
    </section>

    <section class="mt-6 rounded-2xl bg-white p-5 border border-slate-100 shadow-sm">
      <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
        <h2 class="text-lg font-semibold">明细清单</h2>
        <label class="inline-flex items-center gap-2 text-sm">
          <input type="checkbox" v-model="onlyReview" class="rounded border-slate-300 text-teal-700 focus:ring-teal-600" />
          仅显示需复核
        </label>
      </div>
      <p class="text-sm text-slate-500 mt-2">复核阈值：confidence &lt; {{{{ summary.confidence_threshold }}}}</p>

      <div class="overflow-auto mt-4">
        <table class="min-w-full text-sm">
          <thead>
            <tr class="bg-slate-50 text-slate-600">
              <th class="text-left p-3">学号</th>
              <th class="text-left p-3">文件</th>
              <th class="text-left p-3">总分</th>
              <th class="text-left p-3">置信度</th>
              <th class="text-left p-3">复核状态</th>
              <th class="text-left p-3">复核原因（中文）</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in filteredRows" :key="row.source_file" :class="row.review_required ? 'bg-rose-50/40' : 'bg-white'" class="border-b border-slate-100 align-top">
              <td class="p-3 font-medium">{{{{ row.student_id || '-' }}}}</td>
              <td class="p-3">{{{{ row.source_file }}}}</td>
              <td class="p-3">{{{{ row.total_score }}}}</td>
              <td class="p-3">{{{{ row.confidence }}}}</td>
              <td class="p-3">
                <span v-if="row.review_required" class="px-2 py-1 rounded-full text-xs bg-rose-100 text-rose-700">需复核</span>
                <span v-else class="px-2 py-1 rounded-full text-xs bg-emerald-100 text-emerald-700">通过</span>
              </td>
              <td class="p-3">{{{{ row.review_reason }}}}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section class="mt-6 rounded-2xl bg-white p-5 border border-slate-100 shadow-sm">
      <h2 class="text-lg font-semibold">评分说明抽样（中文）</h2>
      <div class="mt-4 space-y-4">
        <article v-for="row in filteredRows.slice(0, 6)" :key="'reason-'+row.source_file" class="rounded-xl border border-slate-100 p-4">
          <p class="font-medium text-slate-700">{{{{ row.source_file }}}}</p>
          <ul class="mt-2 space-y-2 text-sm">
            <li v-for="s in row.scores" :key="row.source_file + s.dimension_key">
              <span class="font-medium text-teal-700">[{{{{ s.dimension_name }}}}]</span>
              {{{{ s.reason }}}}
            </li>
          </ul>
        </article>
      </div>
    </section>
  </div>

  <script>
    const REPORT_DATA = {data_json};
    function escapeHtml(value) {{
      return String(value ?? '')
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#39;');
    }}

    function renderFallback(data) {{
      const root = document.getElementById('app');
      if (!root) return;
      const total = data.summary.total_files || 0;
      const maxBand = Math.max(1, ...data.bands.map(b => b.count || 0));
      const bandRows = data.bands.map(b => {{
        const w = ((b.count || 0) / maxBand) * 100;
        return `
          <div class="bar-row">
            <div>${{escapeHtml(b.label)}}（${{b.min}}-${{b.max}}）：${{b.count}}</div>
            <div class="bar-track"><div class="bar-fill" style="width:${{w}}%"></div></div>
          </div>
        `;
      }}).join('');

      const reasonRows = (data.review_reasons || []).map(r =>
        `<tr><td>${{escapeHtml(r.reason)}}</td><td>${{r.count}}</td></tr>`
      ).join('') || '<tr><td>无</td><td>0</td></tr>';

      const tableRows = (data.rows || []).map(r => `
        <tr>
          <td>${{escapeHtml(r.student_id || '-')}}</td>
          <td>${{escapeHtml(r.source_file)}}</td>
          <td>${{r.total_score}}</td>
          <td>${{r.confidence}}</td>
          <td>${{r.review_required ? '<span class="fallback-badge warn">需复核</span>' : '<span class="fallback-badge ok">通过</span>'}}</td>
          <td>${{escapeHtml(r.review_reason)}}</td>
        </tr>
      `).join('');

      root.innerHTML = `
        <div class="fallback-wrap">
          <div class="fallback-card">
            <h1 style="margin:0 0 8px 0;">评分报告（离线回退模式）</h1>
            <div>run_id：${{escapeHtml(data.meta.run_id)}}</div>
            <div>日期：${{escapeHtml(data.meta.date)}}</div>
            <div>规则：${{escapeHtml(data.meta.rubric_path)}}</div>
            <div>生成时间：${{escapeHtml(data.meta.generated_at)}}</div>
          </div>
          <div class="fallback-grid">
            <div class="fallback-card"><div>总文件数</div><div style="font-size:26px;font-weight:700;margin-top:6px;">${{total}}</div></div>
            <div class="fallback-card"><div>平均分</div><div style="font-size:26px;font-weight:700;margin-top:6px;">${{data.summary.avg_score}} / ${{data.summary.total_score_max}}</div></div>
            <div class="fallback-card"><div>平均置信度</div><div style="font-size:26px;font-weight:700;margin-top:6px;">${{data.summary.avg_confidence}}</div></div>
            <div class="fallback-card"><div>需复核</div><div style="font-size:26px;font-weight:700;margin-top:6px;color:#991b1b;">${{data.summary.review_count}} (${{data.summary.review_ratio}}%)</div></div>
          </div>
          <div class="fallback-card">
            <h2 style="margin:0 0 8px 0;">分数段分布</h2>
            ${{bandRows}}
          </div>
          <div class="fallback-card">
            <h2 style="margin:0 0 8px 0;">复核原因</h2>
            <table class="fallback-table">
              <thead><tr><th>原因</th><th>次数</th></tr></thead>
              <tbody>${{reasonRows}}</tbody>
            </table>
          </div>
          <div class="fallback-card">
            <h2 style="margin:0 0 8px 0;">明细列表</h2>
            <table class="fallback-table">
              <thead>
                <tr><th>学号</th><th>文件</th><th>总分</th><th>置信度</th><th>复核状态</th><th>复核原因（中文）</th></tr>
              </thead>
              <tbody>${{tableRows}}</tbody>
            </table>
          </div>
        </div>
      `;
    }}

    function mountVueApp() {{
      const app = Vue.createApp({{
        data() {{
          return {{
            meta: REPORT_DATA.meta,
            summary: REPORT_DATA.summary,
            bands: REPORT_DATA.bands,
            reviewReasons: REPORT_DATA.review_reasons,
            dimensionAverages: REPORT_DATA.dimension_averages,
            rows: REPORT_DATA.rows,
            onlyReview: false
          }};
        }},
        computed: {{
          filteredRows() {{
            return this.onlyReview ? this.rows.filter(r => r.review_required) : this.rows;
          }}
        }},
        mounted() {{
          this.renderBandChart();
          this.renderReasonChart();
          this.renderDimensionChart();
        }},
        methods: {{
          renderBandChart() {{
            const ctx = document.getElementById('bandChart');
            if (!ctx || !window.Chart) return;
            new Chart(ctx, {{
              type: 'bar',
              data: {{
                labels: this.bands.map(b => `${{b.label}} (${{b.min}}-${{b.max}})`),
                datasets: [{{
                  label: '人数',
                  data: this.bands.map(b => b.count),
                  backgroundColor: ['#f97316', '#eab308', '#14b8a6', '#0ea5e9'],
                  borderRadius: 10
                }}]
              }},
              options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                  legend: {{ display: false }}
                }},
                scales: {{
                  y: {{ beginAtZero: true, ticks: {{ precision: 0 }} }}
                }}
              }}
            }});
          }},
          renderReasonChart() {{
            const ctx = document.getElementById('reasonChart');
            if (!ctx || !window.Chart) return;
            const labels = this.reviewReasons.length ? this.reviewReasons.map(r => r.reason) : ['无'];
            const values = this.reviewReasons.length ? this.reviewReasons.map(r => r.count) : [1];
            new Chart(ctx, {{
              type: 'doughnut',
              data: {{
                labels,
                datasets: [{{
                  data: values,
                  backgroundColor: ['#ef4444', '#f59e0b', '#6366f1', '#10b981', '#0ea5e9'],
                }}]
              }},
              options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                  legend: {{
                    position: 'bottom'
                  }}
                }}
              }}
            }});
          }},
          renderDimensionChart() {{
            const ctx = document.getElementById('dimensionChart');
            if (!ctx || !window.Chart) return;
            new Chart(ctx, {{
              type: 'radar',
              data: {{
                labels: this.dimensionAverages.map(d => d.name),
                datasets: [{{
                  label: '维度均分',
                  data: this.dimensionAverages.map(d => d.avg_score),
                  backgroundColor: 'rgba(20, 184, 166, 0.20)',
                  borderColor: '#0f766e',
                  pointBackgroundColor: '#0f766e'
                }}]
              }},
              options: {{
                responsive: true,
                maintainAspectRatio: false,
                scales: {{
                  r: {{
                    beginAtZero: true
                  }}
                }}
              }}
            }});
          }}
        }}
      }});
      app.mount('#app');
    }}

    try {{
      if (window.Vue && typeof Vue.createApp === 'function') {{
        mountVueApp();
      }} else {{
        renderFallback(REPORT_DATA);
      }}
    }} catch (err) {{
      console.error('Vue render failed, fallback mode enabled.', err);
      renderFallback(REPORT_DATA);
    }}
  </script>
</body>
</html>"""


def main():
    parser = argparse.ArgumentParser(description="Generate a single-file Vue+Tailwind grading report HTML.")
    parser.add_argument("--manifest", required=True, help="Path to run manifest.yaml")
    parser.add_argument("--raw", default="", help="Path to grading_raw.jsonl (optional)")
    parser.add_argument("--output", default="", help="Path to report.html (optional)")
    args = parser.parse_args()

    manifest_path = Path(args.manifest).resolve()
    manifest = read_yaml(manifest_path)
    repo_root = find_repo_root_from_manifest(manifest_path)

    raw_path = Path(args.raw).resolve() if args.raw else None
    if raw_path is None:
        inferred = manifest.get("trace", {}).get("grading_raw_jsonl", "")
        raw_path = Path(inferred)
        if not raw_path.is_absolute():
            raw_path = (repo_root / raw_path).resolve()

    output_path = Path(args.output).resolve() if args.output else None
    if output_path is None:
        out_name = manifest.get("artifacts", {}).get("report_html", "report.html")
        output_dir = Path(manifest.get("output_dir", "."))
        if not output_dir.is_absolute():
            output_dir = (repo_root / output_dir).resolve()
        output_path = output_dir / out_name

    payload = build_payload(manifest_path, raw_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_html(payload), encoding="utf-8")
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
