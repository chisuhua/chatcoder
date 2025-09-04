# tests/conftest.py
import sys
from unittest.mock import patch
from pathlib import Path
import tempfile
import pytest
import shutil

# 将项目根目录加入 Python 路径
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

# 导入模块以修改配置
from chatcoder.core.state import TASKS_DIR


@pytest.fixture
def tasks_dir(tmp_path):
    """为每个测试提供一个干净的临时 tasks 目录"""
    temp_tasks = tmp_path / ".chatcoder" / "tasks"
    temp_tasks.mkdir(parents=True, exist_ok=True)

    # 临时修改 TASKS_DIR 全局变量
    original_tasks_dir = TASKS_DIR
    from chatcoder.core.state import get_tasks_dir

    # 修改模块级变量
    get_tasks_dir.__globals__["TASKS_DIR"] = temp_tasks

    yield temp_tasks

    # 恢复（可选）
    get_tasks_dir.__globals__["TASKS_DIR"] = original_tasks_dir
