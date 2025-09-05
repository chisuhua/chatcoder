# tests/test_context.py
import pytest
from chatcoder.core.context import generate_context_snapshot, parse_context_file, load_core_patterns_from_config
from pathlib import Path

def test_parse_context_file_success(temp_project_dir):
    """测试成功解析 context.yaml"""
    ctx = parse_context_file()
    assert isinstance(ctx, dict)
    assert ctx["project_name"] == "Test Project"
    assert ctx["project_language"] == "python"

def test_parse_context_file_not_found(temp_project_dir):
    """测试 context.yaml 不存在的情况"""
    # 在 conftest 的 fixture 作用域内操作，这里直接测试异常处理逻辑可能不够直观
    # 更好的方式是在一个不包含 .chatcoder/context.yaml 的目录测试
    # 但 conftest 已经创建了，我们测试加载默认值或空值的情况
    # 或者手动删除文件进行测试
    Path(".chatcoder/context.yaml").unlink() # 删除文件
    with pytest.raises(FileNotFoundError):
        parse_context_file()

def test_generate_context_snapshot_basic(temp_project_dir):
    """测试生成上下文快照的基本功能"""
    snapshot_data = generate_context_snapshot()
    
    assert "project_name" in snapshot_data
    assert "project_language" in snapshot_data
    assert "project_type" in snapshot_data
    assert "context_snapshot" in snapshot_data
    assert "core_files" in snapshot_data
    
    # 检查是否扫描到了模拟的文件
    core_files = snapshot_data["core_files"]
    assert "main.py" in [Path(p).name for p in core_files.keys()]
    assert "utils.py" in [Path(p).name for p in core_files.keys()]
    assert "models.py" in [Path(p).name for p in core_files.keys()]

def test_load_core_patterns_from_config(temp_project_dir):
    """测试从 config.yaml 加载 core_patterns"""
    patterns = load_core_patterns_from_config()
    assert isinstance(patterns, list)
    assert "**/*.py" in patterns
