"""模板注册 — 所有 scaffold 模板集中在此注册"""

from seed_tools.templates.react_shadcn import TEMPLATE as react_shadcn
from seed_tools.templates.fastapi import TEMPLATE as fastapi
from seed_tools.templates.flask import TEMPLATE as flask
from seed_tools.templates.cli import TEMPLATE as cli
from seed_tools.templates.package import TEMPLATE as package
from seed_tools.templates.wx_minigame import TEMPLATE as wx_minigame

TEMPLATES = {
    "react-shadcn": react_shadcn,
    "fastapi": fastapi,
    "flask": flask,
    "cli": cli,
    "package": package,
    "wx-minigame": wx_minigame,
}
