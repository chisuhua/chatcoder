# tests/conftest.py
import tempfile
import os
import pytest
import yaml
from pathlib import Path
from chatcoder.core.orchestrator import TaskOrchestrator
from chatcoder.core.engine import WorkflowEngine
from chatcoder.core.manager import AIInteractionManager

# 这个 fixture 会为每个测试函数创建一个独立的临时目录，
# 并将当前工作目录切换到该目录，测试结束后自动清理。
@pytest.fixture
def temp_project_dir():
    """提供一个临时项目目录，模拟 .chatcoder 文件夹。"""
    with tempfile.TemporaryDirectory() as tmpdirname:
        original_cwd = os.getcwd()
        os.chdir(tmpdirname)
        
        # 创建模拟的 .chatcoder 目录结构
        chatcoder_dir = Path(".chatcoder")
        chatcoder_dir.mkdir(exist_ok=True)
        (chatcoder_dir / "tasks").mkdir(exist_ok=True)
        
        # 创建一个基本的 config.yaml
        config_content = """
project:
  name: "Test Project"
  language: "python"
  type: "cli"
core_patterns:
  - "**/*.py"
exclude_patterns: []
"""
        (chatcoder_dir / "config.yaml").write_text(config_content.strip(), encoding='utf-8')

        # 创建一个基本的 context.yaml
        context_content = """
project_name: "Test Project"
project_language: "python"
project_type: "cli"
framework: "None"
test_runner: "pytest"
format_tool: "black"
"""
        (chatcoder_dir / "context.yaml").write_text(context_content.strip(), encoding='utf-8')

        # 创建一个简单的 workflows 目录和 default.yaml
        workflows_dir = chatcoder_dir / "workflows"
        workflows_dir.mkdir(exist_ok=True)
        workflow_content = """
name: "default"
description: "Standard development workflow"
phases:
  - name: "analyze"
    title: "需求分析"
    template: "analyze"
  - name: "design"
    title: "架构设计"
    template: "design"
  - name: "implement"
    title: "编码实现"
    template: "implement"
  - name: "test"
    title: "测试用例"
    template: "test"
  - name: "summary"
    title: "总结归档"
    template: "summary"
"""
        (workflows_dir / "default.yaml").write_text(workflow_content.strip(), encoding='utf-8')

        # 创建一些模拟的源代码文件用于上下文扫描
        (Path("main.py")).write_text("# This is the main entry point\nprint('Hello')\n", encoding='utf-8')
        (Path("utils.py")).write_text("# Utility functions\ndef helper():\n    pass\n", encoding='utf-8')
        (Path("models.py")).write_text("# Data models\nclass User:\n    pass\n", encoding='utf-8')

        try:
            yield tmpdirname  # 将临时目录路径提供给测试函数
        finally:
            os.chdir(original_cwd) # 测试结束后恢复原始工作目录

# --- 新增 Fixtures 用于服务实例 ---
@pytest.fixture
def task_orchestrator():
    """提供一个 TaskOrchestrator 实例。"""
    return TaskOrchestrator()

@pytest.fixture
def workflow_engine():
    """提供一个 WorkflowEngine 实例。"""
    return WorkflowEngine()

@pytest.fixture
def ai_manager():
    """提供一个 AIInteractionManager 实例。"""
    return AIInteractionManager()

# --- 可选：更复杂的 fixture 来设置初始状态 ---
@pytest.fixture
def sample_task_data():
    """提供一个示例任务数据字典。"""
    return {
        "template": "analyze",
        "description": "Test task for unit test",
        "context": {"rendered": "This is a test prompt."},
        "feature_id": "feat_test_unit",
        "phase": "analyze",
        "status": "pending", # 注意：现在应该使用 TaskStatus.PENDING.value
        "workflow": "default"
    }
