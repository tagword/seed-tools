# Template: cli
# Auto-extracted from scaffold.py

TEMPLATE = {
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
    }
