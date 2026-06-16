# Template: flask
# Auto-extracted from scaffold.py

TEMPLATE = {
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
    }
