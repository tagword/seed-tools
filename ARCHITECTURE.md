# Architecture

## 项目定位

**seed-tools**（PyPI 名 `seed-toolbox`）是 seed 内核的**内置工具层**，提供 LLM Agent 可调用的 40+ 工具。作为 seed 的可选依赖，宿主可按需加载。

```
┌──────────────────────────────────────┐
│   Agent (CodeAgent / 其他宿主)        │  ← 调用工具
├──────────────────────────────────────┤
│         seed-tools                    │  ← 本包
│   setup_builtin_tools() 注册所有工具  │
├──────────────────────────────────────┤
│         seed (kernel)                 │  ← 提供 ToolRegistry 契约
└──────────────────────────────────────┘
```

## 目录结构

```
seed-tools/
│
├── seed_tools/
│   ├── __init__.py          # setup_builtin_tools() — 统一注册入口
│   ├── _registration.py     # 注册辅助逻辑
│   │
│   ├── file.py              # 文件工具：file_read, file_write, file_search
│   ├── artifact_helpers.py  # 制品读取（artifact_read）
│   ├── bash.py              # shell 执行（bash）
│   ├── shell_runner.py      # shell 运行器底层
│   ├── shell_helpers.py     # shell 辅助函数
│   │
│   ├── code_check.py        # 代码检查（ruff/eslint）
│   ├── project.py           # 项目分析（project summary/symbols）
│   ├── symbol.py            # 符号搜索
│   ├── patch.py             # 补丁应用（apply_patch）
│   ├── refactor/            # 代码重构工具（未拆出时在 project 内）
│   │
│   ├── web.py               # 网络工具：web_search, web_fetch
│   ├── browser.py           # 浏览器自动化（browser_* 系列）
│   ├── media.py             # 媒体工具（vision_analyze, audio_transcribe）
│   ├── image_gen.py         # 图像生成
│   ├── music_gen.py         # 音乐生成
│   │
│   ├── db.py                # 数据库工具（SQLite/PostgreSQL/MySQL）
│   ├── git.py               # Git 工具
│   ├── deploy.py            # 部署工具（Dockerfile/Compose/CI）
│   ├── api_docs.py          # API 文档生成
│   ├── diagram.py           # 架构图生成
│   ├── pipeline.py          # 工作流（fix-and-commit / new-feature）
│   ├── scaffold.py          # 项目脚手架
│   │
│   ├── todo.py              # 待办管理
│   ├── misc.py              # 杂项工具（echo, calculate, counter）
│   ├── mcp.py               # MCP 调用工具（mcp_call/mcp_skill）
│   ├── cron.py              # Cron 管理（seed_cron_*）
│   ├── team.py              # 团队工具（call_agent, dispatch, parallel）
│   ├── hub.py               # Agent Hub 通信
│   ├── instruction.py       # 指令发布工具
│   ├── skill_discover.py    # 技能发现
│   ├── notebook.py          # Jupyter notebook 编辑
│   └── imports.py           # 导入辅助
│
├── tests/                   # 工具测试
├── CHANGELOG.md
├── CONTRIBUTING.md
└── pyproject.toml
```

## 工具注册机制

所有工具通过 `setup_builtin_tools(registry: ToolRegistry)` 注册：

```python
from seed_tools import setup_builtin_tools
from seed.core.tool_runtime import ToolRegistry

registry = ToolRegistry()
setup_builtin_tools(registry)  # 注册所有内置工具
```

每个工具模块暴露 `register(registry)` 函数，`__init__.py` 中的 `setup_builtin_tools` 遍历调用各模块的注册函数。

## 工具分类

| 类别 | 工具 | 说明 |
|------|------|------|
| **文件** | file_read, file_write, file_search, grep, glob | 文件系统操作 |
| **Shell** | bash, shell_runner | 命令执行 |
| **代码** | code_check, project, refactor, symbol_search, apply_patch | 代码分析/修改 |
| **Web** | web_search, web_fetch | 网络信息获取 |
| **浏览器** | browser_ensure_running, browser_connect, navigate, screenshot, ... | 浏览器自动化 |
| **数据库** | db (connect/query/execute/schema/models) | 多数据库支持 |
| **Git** | git (全操作) | 版本控制 |
| **DevOps** | deploy, api_docs, diagram, scaffold, pipeline | 开发运维 |
| **多模态** | vision_analyze, audio_transcribe, image_generate, music_generate, video_generate | 媒体生成与分析 |
| **项目管理** | todo, wbs_draft | 任务跟踪 |
| **团队** | call_agent, dispatch, parallel, hub_send | 多 Agent 协作 |
| **记忆** | memory_search, self_reflect | 长期记忆 |
| **MCP** | mcp_call, mcp_skill, mcp_list_skills | MCP 扩展协议 |
| **定时** | seed_cron_path, seed_cron_reload, seed_cron_apply | 定时任务管理 |
| **杂项** | echo, calculate, counter, whoami, tool_search | 通用工具 |

## 关键设计决策

| 决策 | 理由 |
|------|------|
| **独立包而非内嵌 seed** | 宿主可选择性安装，减小内核体积 |
| **ToolRegistry 注册模式** | 工具实现与调度解耦，宿主可覆盖/扩展 |
| **异步工具（async）** | 匹配 LLM 调用与 I/O 密集型操作 |
| **工具沙箱隔离** | shell 工具有限命令白名单，安全约束在 seed 层面 |
