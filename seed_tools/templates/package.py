# Template: package
# Auto-extracted from scaffold.py

TEMPLATE = {
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
    }
