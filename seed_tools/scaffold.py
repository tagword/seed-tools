"""
脚手架工具 — 从模板生成项目骨架

子命令:
  list      列出可用模板  scaffold(template="list")
  fastapi   生成 FastAPI  scaffold(template="fastapi", name="myapi")
  flask     生成 Flask    scaffold(template="flask", name="myapp")
  cli       生成 CLI      scaffold(template="cli", name="mycli")
  package   生成 Package  scaffold(template="package", name="mypkg")
  wx-minigame 生成微信小游戏 project skeleton
  react-shadcn 生成 React + shadcn/ui 设计系统骨架
"""

import os

from seed.core.models import Tool
from seed_tools.templates import TEMPLATES


def scaffold_handler(template: str = "", name: str = "", path: str = "") -> str:
    """
    从模板生成项目骨架。

    Args:
        template: 模板名: fastapi, flask, cli, package, wx-minigame, react-shadcn
        name: 项目名（用于命名目录/包名）
        path: 目标路径（默认当前目录）

    Returns:
        生成结果
    """
    tpl = template.strip().lower()

    if not tpl or tpl == "list":
        result = "📋 **可用模板:**\n\n"
        for key, info in TEMPLATES.items():
            result += f"  📁 `{key}` — {info['description']}\n"
        result += '\n使用方法: scaffold(template="fastapi", name="myproject", path="./myproject")'
        return result

    if tpl not in TEMPLATES:
        available = ", ".join(TEMPLATES.keys())
        return f"❌ 未知模板: {tpl}。可用: {available}"

    target_dir = path or os.getcwd()
    if name:
        target_dir = os.path.join(target_dir, name)

    if os.path.exists(target_dir) and os.listdir(target_dir):
        return f"❌ 目标目录已存在且非空: {target_dir}"

    os.makedirs(target_dir, exist_ok=True)

    files = TEMPLATES[tpl]["files"]
    created = []

    for rel_path, content in files.items():
        final_rel = rel_path
        if name:
            content = content.replace("mypackage", name)
            content = content.replace("mycli", name)
            content = content.replace("mygame", name)
            content = content.replace('"projectname": "mygame"', f'"projectname": "{name}"')
            if "mypackage" in rel_path:
                final_rel = rel_path.replace("mypackage", name)

        full_path = os.path.join(target_dir, final_rel)
        os.makedirs(os.path.dirname(full_path) or target_dir, exist_ok=True)

        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content.lstrip("\n"))
        created.append(os.path.relpath(full_path, target_dir))

    total_bytes = sum(len(TEMPLATES[tpl]["files"][f]) for f in TEMPLATES[tpl]["files"])

    result = [
        f"✅ **项目骨架已创建: {os.path.basename(target_dir)}**",
        f"   模板: {tpl} — {TEMPLATES[tpl]['description']}",
        f"   文件: {len(created)} 个, 约 {total_bytes} 字节",
        "",
        "📂 **文件列表:**",
    ]
    for f in sorted(created):
        result.append(f"  📄 {f}")

    result.extend([
        "",
        "🚀 **下一步:**",
        f"  cd {os.path.basename(target_dir)}",
    ])
    custom_steps = TEMPLATES[tpl].get("next_steps")
    if custom_steps:
        for step in custom_steps:
            result.append(f"  {step}")
    else:
        result.extend([
            "  pip install -r requirements.txt",
            "  python run.py  (或 python app.py)",
        ])

    return "\n".join(result)


scaffold_tool_def = Tool(
    name="scaffold",
    description="从模板生成项目骨架。可用模板: fastapi, flask, cli, package, wx-minigame, react-shadcn。",
    parameters={
        "template": {"type": "string", "required": True, "description": "模板名: fastapi, flask, cli, package, wx-minigame, react-shadcn, list"},
        "name": {"type": "string", "required": False, "description": "项目名（用于命名目录/包）"},
        "path": {"type": "string", "required": False, "description": "目标路径（默认当前目录）"},
    },
    returns="string",
    category="dev",
)
