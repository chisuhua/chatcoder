# chatcoder/core/detector.py
"""项目类型探测器（仅 Python / C++）"""

from pathlib import Path
from typing import List, Dict, Optional
from .utils import load_json_safely, read_file_safely

# ==================== 探测规则 ====================

PROJECT_RULES = {
    "python": [
        {"file": "pyproject.toml"},
        {"file": "requirements.txt"},
        {"file": "setup.py"},
        {"file": "Pipfile"},
    ],
    "python-django": [
        {"file": "manage.py", "required": True},
        {"file": "wsgi.py"},
    ],
    "python-fastapi": [
        {"file": "main.py", "content_contains": "FastAPI"},
        {"file": "app.py", "content_contains": "FastAPI"},
    ],
    "cpp": [
        {"file": "CMakeLists.txt", "required": True},
        {"file": "Makefile"},
        {"file": "configure.ac"},
    ],
    "cpp-bazel": [
        {"file": "WORKSPACE"},
        {"file": "BUILD"},
    ],
}

# ==================== 核心 API ====================

def detect_project_type(root: Path = Path(".")) -> str:
    """
    探测项目类型，返回如 'python-django', 'cpp', 'cpp-bazel'
    优先级：用户配置 > 框架 > 语言
    """
    # 1. 尝试从配置加载（未来扩展）
    # config = _load_config(root)
    # if config and "project_type" in config:
    #     return config["project_type"]

    # 2. 框架/语言探测
    for project_type, rules in PROJECT_RULES.items():
        if _matches_rules(root, rules):
            return project_type

    # 3. fallback
    if (root / "main.py").exists():
        return "python"
    if any(root.glob("**/*.cpp")) or any(root.glob("**/*.cc")):
        return "cpp"
    return "unknown"

# ==================== 私有实现 ====================

def _matches_rules(root: Path, rules: List[Dict]) -> bool:
    """检查是否匹配所有 required 规则"""
    for rule in rules:
        if not _rule_matches(root, rule):
            if rule.get("required", False):
                return False
    return True

def _rule_matches(root: Path, rule: Dict) -> bool:
    """检查单个规则是否匹配"""
    file_path = root / rule["file"]
    
    if not file_path.exists():
        return False

    content_contains = rule.get("content_contains")
    if content_contains:
        content = read_file_safely(file_path)
        if content is None or content_contains not in content:
            return False

    return True
