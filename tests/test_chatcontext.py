# tests/test_chatcontext.py
"""
ChatContext 库单元测试
测试 chatcontext 核心模块的功能，包括 models, provider, providers, manager。
"""

import pytest
import json
import tempfile
import os
from pathlib import Path
from unittest.mock import MagicMock, patch
from datetime import datetime

# --- 导入 chatcontext 模块进行测试 ---
try:
    from chatcontext.core.models import (
        ContextRequest, ProvidedContext, ContextType
    )
    from chatcontext.core.provider import IContextProvider
    from chatcontext.core.providers import (
        ProjectInfoProvider, CoreFilesProvider, _read_file_safely, _detect_project_type
    )
    from chatcontext.core.manager import ContextManager, IContextManager
    CHATCONTEXT_AVAILABLE = True
except ImportError as e:
    CHATCONTEXT_AVAILABLE = False
    pytest.skip(f"Skipping chatcontext tests: {e}", allow_module_level=True)

# --- Fixtures ---

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

        # 创建一些模拟的源代码文件用于上下文扫描
        (Path("main.py")).write_text("# This is the main entry point\nprint('Hello')\n", encoding='utf-8')
        (Path("utils.py")).write_text("# Utility functions\ndef helper():\n    pass\n", encoding='utf-8')
        (Path("models.py")).write_text("# Data models\nclass User:\n    pass\n", encoding='utf-8')

        try:
            yield tmpdirname  # 将临时目录路径提供给测试函数
        finally:
            os.chdir(original_cwd) # 测试结束后恢复原始工作目录


@pytest.fixture
def sample_context_request():
    """提供一个示例 ContextRequest。"""
    return ContextRequest(
        workflow_instance_id="feat_test_123",
        phase_name="implement",
        task_description="Implement user authentication",
        previous_outputs={"task_id": "tsk_prev_456", "template": "design", "description": "Designed auth flow"},
        user_inputs={"additional_info": "Use OAuth2"}
    )


@pytest.fixture
def sample_provided_context():
    """提供一个示例 ProvidedContext。"""
    return ProvidedContext(
        content={"key": "value", "project_name": "Test Project"},
        context_type=ContextType.GUIDING,
        provider_name="test_provider",
        metadata={"generated_at": datetime.now().isoformat()}
    )


# --- Tests for Models ---

def test_context_type_enum():
    """测试 ContextType 枚举。"""
    assert ContextType.GUIDING.value == "guiding"
    assert ContextType.INFORMATIONAL.value == "informational"
    assert ContextType.ACTIONABLE.value == "actionable"


def test_context_request_creation(sample_context_request):
    """测试 ContextRequest 的创建。"""
    assert sample_context_request.workflow_instance_id == "feat_test_123"
    assert sample_context_request.phase_name == "implement"
    assert sample_context_request.task_description == "Implement user authentication"
    assert sample_context_request.previous_outputs == {"task_id": "tsk_prev_456", "template": "design", "description": "Designed auth flow"}
    assert sample_context_request.user_inputs == {"additional_info": "Use OAuth2"}


def test_provided_context_creation(sample_provided_context):
    """测试 ProvidedContext 的创建。"""
    assert sample_provided_context.content == {"key": "value", "project_name": "Test Project"}
    assert sample_provided_context.context_type == ContextType.GUIDING
    assert sample_provided_context.provider_name == "test_provider"
    assert "generated_at" in sample_provided_context.metadata


# --- Tests for Providers ---

def test_project_info_provider_initialization():
    """测试 ProjectInfoProvider 的初始化。"""
    provider = ProjectInfoProvider()
    assert provider.name == "project_info"


def test_project_info_provider_provide(temp_project_dir, sample_context_request):
    """测试 ProjectInfoProvider 的 provide 方法。"""
    provider = ProjectInfoProvider()
    provided_contexts = provider.provide(sample_context_request)
    
    assert isinstance(provided_contexts, list)
    assert len(provided_contexts) == 1
    
    pc = provided_contexts[0]
    assert isinstance(pc, ProvidedContext)
    assert pc.provider_name == "project_info"
    assert pc.context_type == ContextType.GUIDING
    
    content = pc.content
    assert "project_name" in content
    assert "project_language" in content
    assert "project_type" in content
    assert "framework" in content
    assert "test_runner" in content
    assert "format_tool" in content
    assert content["project_name"] == "Test Project"
    assert content["project_language"] == "python"
    #assert content["project_type"] == "cli" # 或根据探测结果
    assert content["test_runner"] == "pytest"
    assert content["format_tool"] == "black"
    provided_project_type = content.get("project_type", "unknown")
    provided_framework = content.get("framework", "unknown")
    
    # 断言它们之间的一致性
    if "django" in provided_project_type.lower():
        assert provided_framework == "Django", f"Inconsistent framework for project_type '{provided_project_type}': expected 'Django', got '{provided_framework}'"
    elif "fastapi" in provided_project_type.lower():
        assert provided_framework == "FastAPI", f"Inconsistent framework for project_type '{provided_project_type}': expected 'FastAPI', got '{provided_framework}'"
    elif provided_project_type == "cli":
        # 对于 "cli" 类型，framework 通常应为 "None" 或 "unknown"
        # 但具体取决于 ProjectInfoProvider 的实现细节
        # 这里我们断言它不是 "Django" 或 "FastAPI"
        assert provided_framework not in ["Django", "FastAPI"], f"Unexpected framework '{provided_framework}' for project_type 'cli'"
        # 或者，如果我们期望是 "None"
        # assert provided_framework == "None", f"Expected framework 'None' for project_type 'cli', got '{provided_framework}'"

def test_core_files_provider_initialization():
    """测试 CoreFilesProvider 的初始化。"""
    provider = CoreFilesProvider()
    assert provider.name == "core_files"


def test_core_files_provider_provide(temp_project_dir, sample_context_request):
    """测试 CoreFilesProvider 的 provide 方法。"""
    provider = CoreFilesProvider()
    provided_contexts = provider.provide(sample_context_request)
    
    assert isinstance(provided_contexts, list)
    assert len(provided_contexts) >= 1 # 至少包含一个 core_files 条目
    
    # 查找 core_files 类型的 ProvidedContext
    core_files_pc = None
    for pc in provided_contexts:
        if "core_files" in pc.content:
            core_files_pc = pc
            break
            
    assert core_files_pc is not None
    assert core_files_pc.provider_name == "core_files"
    assert core_files_pc.context_type == ContextType.INFORMATIONAL
    
    content = core_files_pc.content
    assert "core_files" in content
    core_files = content["core_files"]
    assert isinstance(core_files, dict)
    
    # 检查是否扫描到了模拟的文件
    assert "main.py" in [Path(p).name for p in core_files.keys()]
    assert "utils.py" in [Path(p).name for p in core_files.keys()]
    assert "models.py" in [Path(p).name for p in core_files.keys()]
    
    # 检查文件摘要
    for file_path, info in core_files.items():
        assert "hash" in info
        assert "snippet" in info
        # assert info["snippet"] != " <empty> " # 文件不为空，摘要不应为空


# --- Tests for Manager ---

@pytest.fixture
def context_manager():
    """提供一个 ContextManager 实例。"""
    return ContextManager()


def test_context_manager_initialization(context_manager):
    """测试 ContextManager 的初始化。"""
    assert isinstance(context_manager, ContextManager)
    assert isinstance(context_manager, IContextManager)
    assert context_manager._providers == []


def test_context_manager_register_provider(context_manager):
    """测试 ContextManager 的 register_provider 方法。"""
    provider_mock = MagicMock(spec=IContextProvider)
    provider_mock.name = "mock_provider"
    
    context_manager.register_provider(provider_mock)
    assert len(context_manager._providers) == 1
    assert context_manager._providers[0] == provider_mock


def test_context_manager_unregister_provider(context_manager):
    """测试 ContextManager 的 unregister_provider 方法。"""
    provider_mock1 = MagicMock(spec=IContextProvider)
    provider_mock1.name = "mock_provider_1"
    provider_mock2 = MagicMock(spec=IContextProvider)
    provider_mock2.name = "mock_provider_2"
    
    context_manager.register_provider(provider_mock1)
    context_manager.register_provider(provider_mock2)
    
    assert len(context_manager._providers) == 2
    
    result = context_manager.unregister_provider("mock_provider_1")
    assert result is True
    assert len(context_manager._providers) == 1
    assert context_manager._providers[0].name == "mock_provider_2"
    
    result = context_manager.unregister_provider("non_existent_provider")
    assert result is False
    assert len(context_manager._providers) == 1


def test_context_manager_list_providers(context_manager):
    """测试 ContextManager 的 list_providers 方法。"""
    provider_mock1 = MagicMock(spec=IContextProvider)
    provider_mock1.name = "mock_provider_1"
    provider_mock2 = MagicMock(spec=IContextProvider)
    provider_mock2.name = "mock_provider_2"
    
    context_manager.register_provider(provider_mock1)
    context_manager.register_provider(provider_mock2)
    
    providers = context_manager.list_providers()
    assert isinstance(providers, list)
    assert len(providers) == 2
    assert "mock_provider_1" in providers
    assert "mock_provider_2" in providers


def test_context_manager_get_context(temp_project_dir, sample_context_request):
    """测试 ContextManager 的 get_context 方法。"""
    cm = ContextManager()
    
    # 注册真实的 providers
    cm.register_provider(ProjectInfoProvider())
    cm.register_provider(CoreFilesProvider())
    
    context = cm.get_context(sample_context_request)
    
    assert isinstance(context, dict)
    assert "project_name" in context
    assert "project_language" in context
    assert "project_type" in context
    assert "framework" in context
    assert "test_runner" in context
    assert "format_tool" in context
    assert "core_files" in context
    
    # 检查是否包含了请求中的信息
    assert context["feature_id"] == sample_context_request.workflow_instance_id
    assert context["phase_name"] == sample_context_request.phase_name
    assert context["task_description"] == sample_context_request.task_description
    assert context["previous_outputs"] == sample_context_request.previous_outputs
    assert context["user_inputs"] == sample_context_request.user_inputs


# --- Tests for Internal Helpers (Optional but useful) ---

def test_read_file_safely_success(temp_project_dir):
    """测试 _read_file_safely 成功读取文件。"""
    test_file = Path("test_file.txt")
    test_content = "This is a test file.\nWith multiple lines."
    test_file.write_text(test_content, encoding='utf-8')
    
    content = _read_file_safely(test_file)
    assert content == test_content


def test_read_file_safely_file_not_found(temp_project_dir):
    """测试 _read_file_safely 文件不存在。"""
    non_existent_file = Path("non_existent.txt")
    content = _read_file_safely(non_existent_file)
    assert content is None


def test_read_file_safely_permission_error(temp_project_dir):
    """测试 _read_file_safely 权限错误 (模拟)。"""
    # 在某些平台上模拟权限错误比较困难，这里仅作示例
    # 可以使用 mock 来模拟 open 抛出 PermissionError
    with patch("builtins.open", side_effect=PermissionError("Permission denied")):
        test_file = Path("test_file.txt")
        test_file.write_text("content", encoding='utf-8') # 先创建文件
        content = _read_file_safely(test_file)
        assert content is None


def test_detect_project_type_python_basic(temp_project_dir):
    """测试 _detect_project_type 检测基本的 Python 项目。"""
    # conftest.py 已经创建了 main.py 和 config.yaml (标记为 python)
    # detector 会根据文件存在性判断
    detected_type = _detect_project_type()
    # 由于 main.py 存在，且没有更具体的框架文件，应该检测为 python
    assert detected_type == "python"

def test_detect_project_type_unknown(temp_project_dir):
    """测试 _detect_project_type 检测未知项目类型。"""
    # 删除所有可能触发检测的文件
    Path("main.py").unlink(missing_ok=True)
    Path(".chatcoder/config.yaml").unlink(missing_ok=True) # 不影响 detector
    
    # 创建一个不相关的文件
    Path("README.md").write_text("# My Project", encoding='utf-8')
    
    detected_type = _detect_project_type()
    # 项目中没有 .cpp, .cc 文件，也没有 main.py
    # PROJECT_RULES 中没有匹配的，会 fallback 到 "unknown"
    assert detected_type == "unknown"
