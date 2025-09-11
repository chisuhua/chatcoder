# chatcoder/tests/conftest.py
"""
ChatCoder 测试配置和共享 fixtures
使用 pytest fixtures 来管理测试依赖和状态。
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

# --- 导入被测试的模块中的类，以便于 mock ---
CHATCODER_MODULE = 'chatcoder.core.chatcoder'
CLI_MODULE = 'chatcoder.cli'

# --- Pytest Fixtures ---

@pytest.fixture(scope="session")
def anyio_backend():
    """为使用 anyio 的异步测试提供后端（如果需要）"""
    return 'asyncio' # 或 'trio'

@pytest.fixture(scope="function")
def isolated_filesystem():
    """
    提供一个隔离的临时文件系统。
    在测试前后自动创建和清理临时目录，并切换当前工作目录。
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        original_cwd = os.getcwd()
        os.chdir(temp_path)
        
        # 确保 .chatcoder 目录结构存在，模拟初始化后的状态
        (temp_path / ".chatcoder" / "tasks").mkdir(parents=True, exist_ok=True)
        
        yield temp_path
        
        os.chdir(original_cwd) # 测试结束后恢复原始目录

# --- 为 ChatCoder 服务提供 Mock 依赖 ---
# 使用 patch 直接替换 chatcoder.core.chatcoder 模块中的导入

@pytest.fixture(scope="function")
def mock_chatflow_components():
    """
    Fixture to mock all necessary chatflow components imported in chatcoder.core.chatcoder.
    Returns a dictionary of the mock instances.
    """
    # Patch the classes imported *inside* chatcoder.core.chatcoder
    with patch(f'{CHATCODER_MODULE}.WorkFlowEngine') as mock_engine_class, \
         patch(f'{CHATCODER_MODULE}.FileWorkflowStateStore') as mock_store_class:

        # Create mock instances that the classes will return
        mock_engine_instance = MagicMock()
        mock_store_instance = MagicMock()

        # Configure the classes to return the mock instances when instantiated
        mock_engine_class.return_value = mock_engine_instance
        mock_store_class.return_value = mock_store_instance

        yield {
            'engine_class': mock_engine_class,
            'store_class': mock_store_class,
            'engine_instance': mock_engine_instance,
            'store_instance': mock_store_instance,
        }

@pytest.fixture(scope="function")
def mock_chatcontext_components():
    """
    Fixture to mock all necessary chatcontext components imported in chatcoder.core.chatcoder.
    Returns a dictionary of the mock instances.
    """
    with patch(f'{CHATCODER_MODULE}.ContextManager') as mock_manager_class:

        mock_manager_instance = MagicMock()

        mock_manager_class.return_value = mock_manager_instance

        yield {
            'manager_class': mock_manager_class,
            'manager_instance': mock_manager_instance,
        }

# --- ChatCoder Service Fixture ---
@pytest.fixture(scope="function")
def chatcoder_service(isolated_filesystem, mock_chatflow_components, mock_chatcontext_components):
    """
    Provides a ChatCoder service instance with mocked dependencies.
    This is the main entry point for testing the ChatCoder class logic.
    """
    temp_dir = isolated_filesystem
    # Ensure the tasks directory path used by ChatCoder matches the isolated fs
    mock_chatflow_components['store_instance'].base_path = str(temp_dir / ".chatcoder" / "tasks")

    # Import and instantiate ChatCoder *inside* the patch context
    # so it uses the mocked dependencies
    from chatcoder.core.chatcoder import ChatCoder
    
    # Dummy config and context data for initialization
    dummy_config = {"dummy": "config"}
    dummy_context = {"dummy": "context"}

    chatcoder_instance = ChatCoder(config_data=dummy_config, context_data=dummy_context)
    
    yield {
        'service': chatcoder_instance,
        'mocks': {
            'chatflow': mock_chatflow_components,
            'chatcontext': mock_chatcontext_components,
        },
        'temp_dir': temp_dir
    }
    # Fixture cleanup happens automatically when exiting the 'with patch' blocks

# --- CLI Testing Fixtures ---
@pytest.fixture
def runner():
    """Provide a Click CliRunner instance for testing CLI commands."""
    from click.testing import CliRunner
    return CliRunner()

@pytest.fixture
def mock_cli_chatcoder():
    """
    Mock the ChatCoder class specifically for CLI tests.
    This patches the import in cli.py.
    """
    with patch(f'{CLI_MODULE}.ChatCoder') as mock_chatcoder_class:
        mock_instance = MagicMock()
        # Set default return values for methods that CLI commands expect to call
        mock_instance.is_project_initialized.return_value = True
        mock_instance.list_available_workflows.return_value = ["default", "custom"]
        mock_instance.get_all_features_status.return_value = [
            {"feature_id": "feat_1", "description": "Test Feature 1", "status": "in_progress", "progress": "1/2"}
        ]
        mock_instance.start_new_feature.return_value = {"feature_id": "feat_new_123", "description": "New Feature"}
        mock_instance.generate_prompt_for_current_task.return_value = "Generated prompt content for task."
        mock_instance.confirm_task_and_advance.return_value = {"next_phase": "design", "reason": "Standard flow"}
        mock_instance.preview_prompt_for_phase.return_value = "Preview of prompt for phase."
        mock_instance.apply_task.return_value = True
        
        mock_chatcoder_class.return_value = mock_instance
        yield mock_instance
    # patch automatically stops
