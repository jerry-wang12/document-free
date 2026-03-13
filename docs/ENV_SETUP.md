# 本地环境安装与配置（老师使用版）

本文档用于在老师电脑上完成一次性环境配置，确保可在本地通过 Agent 处理文档评分任务。

## 1. 适用范围

- 项目路径：`document-free`
- 使用方式：本地 Codex + Skills（对话驱动）
- 支持文档：`PDF / DOCX / XLSX / PPTX`
- 支持系统：`macOS`、`Windows 10/11`

## 2. 必装软件

### 2.1 Codex 桌面端

- 安装并登录 Codex（本项目通过 Skills 触发文档工作流）

### 2.2 Node.js 与 pnpm

- Node.js：建议 `>= 20`
- npm：随 Node 安装
- pnpm：建议 `>= 8`

### 2.3 Python

- Python：建议 `>= 3.10`
- 用于部分 Skills 内置脚本（如文档解析、报告导出）

### 2.4 文档系统依赖

以下依赖来自已安装的 `docx/xlsx/pdf/pptx` skills：

- LibreOffice（`soffice`）：Office 转换、公式重算
- Poppler（`pdftoppm` / `pdftotext`）：PDF 渲染与提取
- pandoc：DOCX 文本抽取（含修订）

## 3. 按系统安装

### 3.1 macOS（Homebrew）

```bash
# Node / Python
brew install node python pnpm

# 文档依赖
brew install --cask libreoffice
brew install poppler pandoc
```

### 3.2 Windows 10/11（PowerShell + winget）

以“管理员 PowerShell”执行：

```powershell
# Node / Python / pnpm
winget install OpenJS.NodeJS.LTS
winget install Python.Python.3.12
npm install -g pnpm

# 文档依赖
winget install TheDocumentFoundation.LibreOffice
winget install oschwartz10612.Poppler
winget install JohnMacFarlane.Pandoc
```

如果 `pdftoppm` 无法识别，补充 PATH（示例）：

```powershell
setx PATH "$env:PATH;C:\Program Files\poppler\Library\bin"
```

然后重开终端。

## 4. 安装后校验

### 4.1 macOS / Linux 终端

```bash
node -v
npm -v
pnpm -v
python3 --version
soffice --version
pdftoppm -v
pandoc --version
```

### 4.2 Windows PowerShell

```powershell
node -v
npm -v
pnpm -v
py -3 --version
soffice --version
pdftoppm -v
pandoc --version
```

如果命令找不到，可以再检查：

```powershell
where soffice
where pdftoppm
where pandoc
```

## 5. Python 包建议

### 5.1 macOS / Linux

```bash
python3 -m pip install -U pyyaml python-docx openpyxl pandas fpdf pypdf pdfplumber
python3 -m pip install -U "markitdown[pptx]" Pillow
```

### 5.2 Windows

```powershell
py -3 -m pip install -U pyyaml python-docx openpyxl pandas fpdf pypdf pdfplumber
py -3 -m pip install -U "markitdown[pptx]" Pillow
```

快速校验（两端都可）：

```bash
python3 - <<'PY'
import importlib.util
mods=["yaml","docx","openpyxl","pandas","fpdf","pypdf","pdfplumber"]
for m in mods:
    print(f"{m}: {'OK' if importlib.util.find_spec(m) else 'MISSING'}")
PY
```

Windows 可改为：

```powershell
py -3 - <<'PY'
import importlib.util
mods=["yaml","docx","openpyxl","pandas","fpdf","pypdf","pdfplumber"]
for m in mods:
    print(f"{m}: {'OK' if importlib.util.find_spec(m) else 'MISSING'}")
PY
```

## 6. 技能安装（项目级）

在项目根目录执行：

```bash
npx skills add https://github.com/anthropics/skills --skill docx xlsx pdf pptx --agent codex --yes --copy
```

安装后检查：

macOS / Linux：

```bash
ls .agents/skills
```

Windows PowerShell：

```powershell
Get-ChildItem .agents/skills
```

应包含：

- `docx`
- `xlsx`
- `pdf`
- `pptx`
- `teacher-grading-agent`
- `rubric-builder`
- `evidence-grader`
- `result-exporter`

## 7. 目录初始化检查

确保存在以下目录：

```text
data/rules/YYYY-MM-DD/
data/submissions/YYYY-MM-DD/
data/outputs/YYYY-MM-DD/
data/runs/YYYY-MM-DD/
```

并准备：

- `data/rules/rubric.template.yaml`
- `data/runs/manifest.template.yaml`

## 8. 首次运行建议（最小验证）

1. 放入测试规则到 `data/rules/<date>/`
2. 放入测试文档到 `data/submissions/<date>/`
3. 在 Codex 对话中发送：

```text
请使用 teacher-grading-agent：
按 data/rules/<date>/rubric-demo.yaml
评分 data/submissions/<date>/ 下全部文件，
输出 result.xlsx、review_queue.xlsx、report.html，
并在 data/runs/<date>/ 写入 run 追踪信息。
```

4. 检查输出：
- `data/outputs/<date>/<run-id>/report.html`
- `data/outputs/<date>/<run-id>/result.xlsx`
- `data/outputs/<date>/<run-id>/review_queue.xlsx`

## 9. 常见问题

### 9.1 `report.html` 打开空白或样式缺失

- 该模板使用 CDN 加载 Vue/Tailwind/Chart.js
- 请确认本机可访问外网 CDN

### 9.2 `soffice` / `pdftoppm` 找不到（Windows 常见）

- 确认软件已安装
- 用 `where soffice`、`where pdftoppm` 检查路径
- 若未找到，补 PATH 后重开终端

### 9.3 评分结果中出现英文复核原因

- 使用项目内 `result-exporter` 的报告脚本会自动中文化常见复核原因：

```bash
python3 .agents/skills/result-exporter/references/generate_report_html.py \
  --manifest data/runs/<date>/<run-id>/manifest.yaml
```

Windows：

```powershell
py -3 .agents/skills/result-exporter/references/generate_report_html.py `
  --manifest data/runs/<date>/<run-id>/manifest.yaml
```

## 10. 配置完成后

- 重启 Codex，确保新装技能全部生效
- 建议每次评分使用新 `run-id`，避免覆盖历史结果
