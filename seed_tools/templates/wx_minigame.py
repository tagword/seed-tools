# Template: wx-minigame
# Auto-extracted from scaffold.py

TEMPLATE = {
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
    }
