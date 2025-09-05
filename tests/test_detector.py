# tests/test_detector.py 
import pytest
from chatcoder.core.detector import detect_project_type
from pathlib import Path
import tempfile
import os

def test_detect_project_type_python_basic(temp_project_dir):
    """测试检测基本的 Python 项目 (由 conftest.py 的 fixture 创建的文件触发)"""
    detected_type = detect_project_type()
    assert detected_type == "python"

def test_detect_project_type_unknown():
    """测试检测未知项目类型 (使用完全独立的临时目录)"""
    # 使用 tempfile.TemporaryDirectory 创建一个与 conftest 完全无关的临时目录
    with tempfile.TemporaryDirectory() as clean_temp_dir:
        original_cwd = os.getcwd()
        try:
            os.chdir(clean_temp_dir)
            
            # 确保这个新目录是完全空的，或者只包含我们明确放入的文件
            temp_path = Path(clean_temp_dir)
            
            # 再次显式确保没有可能触发检测的文件
            files_to_ensure_absent = [
                "main.py", "pyproject.toml", "requirements.txt", "setup.py", "Pipfile",
                "manage.py", "app.py", "wsgi.py",
                "CMakeLists.txt", "Makefile", "configure.ac",
                "WORKSPACE", "BUILD"
            ]
            
            for fname in files_to_ensure_absent:
                (temp_path / fname).unlink(missing_ok=True)
                
            # 确保没有 .cpp 或 .cc 文件
            # (glob 在空目录不会有结果)
            
            # 创建一个不相关的文件
            (temp_path / "README.md").write_text("# My Project", encoding='utf-8')
            
            # 在这个完全干净的环境中执行检测
            detected_type = detect_project_type(temp_path)
            
            # 断言结果
            assert detected_type == "unknown"
            
        finally:
            os.chdir(original_cwd)
