# 审计报告: seed-tools

> 日期: 2026-06-16
> 范围: `seed-tools/` — 53 个 Python 文件，10,228 行

---

## 汇总

| 严重度 | 数量 | 关键项 |
|--------|------|--------|
| 🔴 架构 | 2 | scaffold.py + browser.py 严重超限 |
| 🟡 测试 | 2 | 测试覆盖严重不足 + 测试脆弱性已修复 |
| 🟢 低风险 | 3 | 依赖声明缺失、废弃 API 使用、HTTP 库不统一 |
| ✅ 安全 | — | 浏览器 SSRF 防护完善，无注入漏洞 |

---

## 🔴 A1: scaffold.py 1263 行单函数

**位置**: `seed_tools/scaffold.py`
**严重度**: 严重
**说明**: 单文件 1263 行（上限 400 的 3x），**仅 1 个函数** `scaffold_handler()`，内联了 fastapi/flask/cli/package/react-shadcn 共 5 个完整模板的 JSON 数据。
**影响**: 可维护性差；模板数据膨胀后更难扩展。
**建议**: 将模板数据拆到 `seed_tools/templates/` 目录下，每个模板一个独立 `.py` 文件（或 `.json`），`scaffold_handler` 按 `template` 参数动态加载。

---

## 🔴 A2: browser.py 1265 行

**位置**: `seed_tools/browser.py`
**严重度**: 中
**说明**: 1265 行，内含 6 个 class + 23 个函数。安全机制完善（`assert_safe_navigate_url` + `assert_safe_debug_baseurl`），但体积过大。
**建议**: 拆为 `browser_http.py`（HTTP客户端+IP安全检测）、`browser_launch.py`（浏览器进程管理启动）、`browser.py`（保留核心 BrowserManager）。

---

## 🟡 A3: 测试覆盖严重不足

**数据**:
- 53 个 Python 文件（10k+ 行）
- 仅 9 个测试文件（182 行），13 个测试用例
- `browser.py`(1265行)、`scaffold.py`(1263行)、`vision.py`(449行)、`media.py`(452行)、`file.py`(477行) — **零测试覆盖**

**测试脆弱性（已修复）**:
- `test_grep_skips_dist_and_caps_line_length`: `"dist" not in result` 被 tmp_dir 名 `skips_dist` 误命中 → 改为 `"/dist/" not in`
- `test_glob_skips_node_modules`: `"node_modules" not in` 被 tmp_dir 名 `test_glob_skips_node_modules0` 误命中 → 改为 `"/node_modules/" not in`

---

## 🟢 B1: ddgs 依赖未声明

**位置**: `seed_tools/web.py` 第 118 行
**严重度**: 低
**说明**: `web_search_handler` 运行时 `from ddgs import DDGS`，但 `pyproject.toml` 的 `dependencies` 中未列出 `ddgs`（duckduckgo-search）。部署时静默失败。
**建议**: 在 `pyproject.toml` 中加 `ddgs>=1.0.0`，或 try/except ImportError 给更友好报错。

---

## 🟢 B2: media.py 使用废弃 API

**位置**: `seed_tools/media.py` 第 128、160 行
**严重度**: 低
**说明**:
- 第 128 行: `tempfile.mkdtemp()` 创建的临时目录在函数返回后不清理
- 第 160 行: `tempfile.mktemp()` 已废弃（有竞态风险），应改用 `NamedTemporaryFile(delete=False)`

---

## 🟢 B3: HTTP 请求库不统一

**说明**:
- `browser.py` + `hub.py`: 统一用 `httpx.AsyncClient`
- `web.py`: 用 `urllib.request`（同步标准库）
- `media.py`: 用 `requests` 库

**建议**: seed-tools 统一使用 `httpx`。

---

## 🟢 B4: 文件略超限 (400行)

| 文件 | 行数 | 备注 |
|------|------|------|
| `file.py` | 477 | 略微超限，可拆分 artifact_helpers |
| `media.py` | 452 | 略微超限，可拆分音频/视频处理 |
| `vision.py` | 449 | 略微超限 |

---

## ✅ 安全审计通过

- `browser.py` 的 URL 安全检测完善（SSRF 防护、私有地址拦截、环境变量覆盖机制）
- 无 `os.system()`、无 `shell=True`、无 `eval()`/`exec()`
- `subprocess` 调用均使用列表参数（非字符串拼接）
- 没有发现注入漏洞
- 没有裸 `except:`（仅 `_builtin_checks.py` 中用于检查规则，非实际代码）
- 没有 `import *`（仅 scaffold 模板内容，非运行时代码）

---

## 已修复

- ✅ 2 个测试脆弱性问题（`/dist/` 和 `/node_modules/` 路径段检查），13/13 passed
