# Changelog

## 1.0.4 (2026-08-06)

- feat(vision): `_call_vision_llm` 返回 `(text, usage)` — vision_analyze 结果附带 usage 统计（token 用量），media.py 视频分析同步兼容
- chore: bump version to 1.0.3 for next development cycle

## 1.0.3 (2026-07-24)

- feat: MCP skill 工具 — mcp_list_skills/mcp_skill_handler + transport 感知展示
- fix: web_fetch 支持 SEED_WEB_FETCH_MAX_BYTES 截断 + duckduckgo search 结果上限保护
- fix(env): 替换 CODEAGENT_* 环境变量读取为 SEED_* 通过 env_access
- refactor(scaffold): 模板数据拆到 seed_tools/templates/ 目录
- refactor: 清除 seed-tools 对 codeagent 的逆向依赖

## 1.0.2 (2026-06-??)

- feat: team capability Phase 1 — call_agent/dispatch/parallel 工具
- feat: 新增视频生成工具（video_generate, Agnes agnes-video-v2.0）
- feat: 多模态工具 — vision_analyze, image_generate, music_generate
- feat: scaffold 新增 react-shadcn 模板
- feat: instruction_read 工具（锁定发布包读取）

## 1.0.1 (2026-05-??)

- feat: LSP/MCP/patch/symbol/test_run 等开发工具
- feat: 增强 file_write, scaffold, test_run 工具
- feat: cron 管理工具（seed_cron_path/reload/apply）
- fix: 重命名 browser_a→browser, git_a→git 统一导入名
- chore: 清理构建产物，添加 .gitignore

## 1.0.0 (2026-05-??)

- feat: 初始公开发布 — 30+ 内置工具
- 工具分类：文件、Shell、代码分析、Web 搜索、浏览器自动化、
  数据库、Git、部署、项目分析、记忆管理、待办管理等
- docs: README（工具清单 + MIT License）
