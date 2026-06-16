# Template: fastapi
# Auto-extracted from scaffold.py

TEMPLATE = {
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
    }
