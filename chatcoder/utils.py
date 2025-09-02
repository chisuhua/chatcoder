"""
通用工具函数
"""
from pathlib import Path
from typing import Union

def ensure_dir(path: Path):
    """确保目录存在"""
    path.mkdir(parents=True, exist_ok=True)

def read_template(name: str) -> str:
    """读取内置模板"""
    from importlib import resources
    try:
        with resources.open_text('chatcoder.templates', name) as f:
            return f.read()
    except Exception as e:
        raise FileNotFoundError(f"Template {name} not found: {e}")
