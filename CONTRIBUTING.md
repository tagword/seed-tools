# Contributing

## 开发环境

```bash
# 克隆
git clone https://github.com/tagword/seed-tools
cd seed-tools

# 虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# 可编辑安装（含开发依赖）
pip install -e ".[dev]"
```

### 依赖关系

seed-tools 依赖 `seed` 和 `seed-model-providers`：

```bash
# 本地开发时克隆配套包
git clone https://github.com/tagword/seed ../seed
git clone https://github.com/tagword/seed-model-providers ../seed-model-providers
pip install -e ../seed
pip install -e ../seed-model-providers
```

## 测试

```bash
# 全部测试
pytest

# 按工具模块运行
pytest tests/test_file.py -v
pytest tests/test_git.py -v
```

## 添加新工具

1. 在 `seed_tools/` 下创建工具模块（如 `seed_tools/my_tool.py`）
2. 在 `seed_tools/__init__.py` 中注册到 `setup_builtin_tools()`
3. 编写 pytest 测试
4. 更新 `README.md` 工具清单

工具模块的推荐结构：

```python
"""Short description of the tool."""

from seed.core.tool_runtime import ToolRegistry, ToolSpec

def register(registry: ToolRegistry) -> None:
    @registry.tool(
        name="my_tool",
        description="What this tool does",
        parameters={...},  # JSON Schema
    )
    async def my_tool(param1: str, param2: int = 0) -> str:
        """Implement the tool logic."""
        return result
```

## PR 规范

- 分支名：`feat/xxx`、`fix/xxx`、`chore/xxx`
- Commit message 遵循 Conventional Commits
- 新增工具必须附带测试覆盖
- 提交前 `pytest` 全部通过

## 发布流程

```bash
# 1. 更新 pyproject.toml 版本号
# 2. 更新 CHANGELOG.md
# 3. 提交并打 tag
git commit -m "chore: bump version to v1.0.x"
git tag v1.0.x
git push origin v1.0.x
# 4. 构建并发布 PyPI
python -m build
twine upload dist/*
```
