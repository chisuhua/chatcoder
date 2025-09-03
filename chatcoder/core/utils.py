# chatcoder/core/utils.py
"""通用工具函数，无外部依赖"""

import json
from pathlib import Path
from typing import Dict, Any, Optional

def read_file_safely(path: Path, encoding: str = "utf-8") -> Optional[str]:
    """安全读取文件内容"""
    try:
        if path.exists() and path.is_file():
            return path.read_text(encoding=encoding)
    except (UnicodeDecodeError, PermissionError, OSError):
        pass
    return None

def load_json_safely(path: Path) -> Optional[Dict[Any, Any]]:
    """安全加载 JSON 文件"""
    content = read_file_safely(path)
    if content:
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass
    return None

def file_exists_case_sensitive(path: str) -> bool:
    """检查文件是否存在（区分大小写）"""
    p = Path(path)
    if not p.exists():
        return False
    # 检查大小写是否完全匹配
    return p.name in [f.name for f in p.parent.iterdir()]
