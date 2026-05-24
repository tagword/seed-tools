"""
脚手架工具 — 从模板生成项目骨架

子命令:
  list      列出可用模板  scaffold(template="list")
  fastapi   生成 FastAPI  scaffold(template="fastapi", name="myapi")
  flask     生成 Flask    scaffold(template="flask", name="myapp")
  cli       生成 CLI      scaffold(template="cli", name="mycli")
  package   生成 Package  scaffold(template="package", name="mypkg")
"""

import os

from seed.core.models import Tool

# ── 内置模板 ──

TEMPLATES = {
    "fastapi": {
        "description": "FastAPI REST API 项目骨架",
        "files": {
            "requirements.txt": "fastapi>=0.104.0\nuvicorn>=0.24.0\npydantic>=2.0\n",
            "app.py": '''"""FastAPI app entry point"""
from fastapi import FastAPI

app = FastAPI(title="My API", version="0.1.0")


@app.get("/")
def root():
    return {"message": "Hello World"}


@app.get("/health")
def health():
    return {"status": "ok"}
''',
            "run.py": '''"""Run the FastAPI app with uvicorn"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
''',
        },
    },
    "flask": {
        "description": "Flask Web 应用项目骨架",
        "files": {
            "requirements.txt": "flask>=3.0\n",
            "app.py": '''"""Flask app entry point"""
from flask import Flask, jsonify

app = Flask(__name__)


@app.route("/")
def root():
    return jsonify({"message": "Hello World"})


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
''',
        },
    },
    "cli": {
        "description": "Python CLI 工具项目骨架 (argparse)",
        "files": {
            "requirements.txt": "",
            "mycli/__init__.py": "",
            "mycli/cli.py": '''"""CLI entry point"""
import argparse


def main():
    parser = argparse.ArgumentParser(description="CLI tool")
    parser.add_argument("--name", default="World", help="Name to greet")
    args = parser.parse_args()
    print(f"Hello, {args.name}!")


if __name__ == "__main__":
    main()
''',
            "setup.py": '''from setuptools import setup, find_packages

setup(
    name="mycli",
    version="0.1.0",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "mycli=mycli.cli:main",
        ],
    },
)
''',
        },
    },
    "package": {
        "description": "Python 库项目骨架",
        "files": {
            "requirements.txt": "",
            "mypackage/__init__.py": '"""mypackage - A Python package"""\n\n__version__ = "0.1.0"\n',
            "mypackage/core.py": '''"""Core module"""
from typing import Optional


def hello(name: str = "World") -> str:
    """Say hello."""
    return f"Hello, {name}!"
''',
            "tests/__init__.py": "",
            "tests/test_core.py": '''"""Tests for core module"""
from mypackage.core import hello


def test_hello():
    assert hello() == "Hello, World!"
    assert hello("CodeAgent") == "Hello, CodeAgent!"
''',
            "setup.py": '''from setuptools import setup, find_packages

setup(
    name="mypackage",
    version="0.1.0",
    packages=find_packages(),
    python_requires=">=3.9",
)
''',
        },
    },
    "wx-minigame": {
        "description": "微信小游戏项目骨架 (Canvas 2D + game.json)",
        "next_steps": [
            "用微信开发者工具导入本项目目录",
            "AppID 填测试号或你的小程序 AppID",
            "npm install && npm run lint",
            "点击「编译」预览小游戏",
        ],
        "files": {
            "game.js": '''import Main from "./js/main";

new Main();
''',
            "game.json": '''{
  "deviceOrientation": "portrait",
  "showStatusBar": false,
  "networkTimeout": {
    "request": 5000,
    "connectSocket": 5000,
    "uploadFile": 5000,
    "downloadFile": 5000
  }
}
''',
            "project.config.json": '''{
  "description": "微信小游戏",
  "packOptions": { "ignore": [], "include": [] },
  "setting": {
    "urlCheck": false,
    "es6": true,
    "postcss": true,
    "minified": true,
    "newFeature": true
  },
  "compileType": "game",
  "libVersion": "3.5.0",
  "appid": "touristappid",
  "projectname": "mygame",
  "condition": {}
}
''',
            "js/main.js": '''/** @type {WechatMinigame.Canvas} */
const canvas = wx.createCanvas();
const ctx = canvas.getContext("2d");

export default class Main {
  constructor() {
    this.loop = this.loop.bind(this);
    wx.onShow(this.loop);
    this.loop();
  }

  loop() {
    const { windowWidth: w, windowHeight: h } = wx.getSystemInfoSync();
    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = "#1a1a2e";
    ctx.fillRect(0, 0, w, h);
    ctx.fillStyle = "#eee";
    ctx.font = "20px sans-serif";
    ctx.fillText("Hello 微信小游戏", 24, 48);
    requestAnimationFrame(this.loop);
  }
}
''',
            "package.json": '''{
  "name": "mygame",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "lint": "eslint js --ext .js"
  },
  "devDependencies": {
    "eslint": "^9.0.0"
  }
}
''',
            "eslint.config.js": '''export default [
  {
    files: ["js/**/*.js"],
    languageOptions: { ecmaVersion: 2022, sourceType: "module" },
    rules: { "no-unused-vars": "warn", "no-console": "off" },
  },
];
''',
            "README.md": '''# 微信小游戏

1. 用 [微信开发者工具](https://developers.weixin.qq.com/miniprogram/dev/devtools/download.html) 打开本目录
2. 选择「小游戏」→ 导入项目
3. `npm install` 后可用 `npm run lint` 检查 JS
4. 在 CodeAgent 中继续迭代 `js/` 下的游戏逻辑
''',
        },
    },
}


def scaffold_handler(template: str = "", name: str = "", path: str = "") -> str:
    """
    从模板生成项目骨架。

    Args:
        template: 模板名: fastapi, flask, cli, package
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
    description="从模板生成项目骨架。可用模板: fastapi, flask, cli, package, wx-minigame。",
    parameters={
        "template": {"type": "string", "required": True, "description": "模板名: fastapi, flask, cli, package, wx-minigame, list"},
        "name": {"type": "string", "required": False, "description": "项目名（用于命名目录/包）"},
        "path": {"type": "string", "required": False, "description": "目标路径（默认当前目录）"},
    },
    returns="string",
    category="dev",
)
