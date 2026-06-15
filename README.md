# seed-tools

Builtin LLM-callable tools for the [Seed](https://github.com/tagword/seed) kernel.

This package provides a comprehensive set of tools that LLM agents can use to interact with the filesystem, shell, browser, database, git, and more. It depends only on `seed`; hosts like CodeAgent consume this package.

## Tools

| Category | Tools |
|----------|-------|
| **File** | file_read, file_write, file_search, grep_tool, glob_tool, artifact_read |
| **Shell** | bash_tool, bash |
| **Code** | code_check, project, refactor, test_gen |
| **Web** | web_search_tool, web_fetch |
| **Browser** | browser_ensure_running, browser_connect, browser_navigate, browser_screenshot, browser_new_page, browser_targets, browser_status |
| **DB** | db (SQLite / PostgreSQL / MySQL) |
| **Git** | git (full operations) |
| **DevOps** | deploy, deps_check, api_docs, diagram, scaffold, pipeline |
| **Project** | todo_tool, wbs_draft |
| **Memory** | memory_search, self_reflect |
| **Cron** | seed_cron_path, seed_cron_reload, seed_cron_apply |
| **Misc** | echo, calculate, counter, whoami, tool_search_tool, hub_send, notebook_edit_tool |

## License

MIT License

Copyright (c) 2025 Seed Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
