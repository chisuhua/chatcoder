# chatcoder/tests/conftest.py
"""
ChatCoder 测试配置和共享 fixtures
使用 pytest fixtures 来管理测试依赖和状态。
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import MagicMock, patch # 确保移除了 create_autospec

# --- 导入被测试的模块中的类，以便于 mock ---
CHATCODER_MODULE = 'chatcoder.core.chatcoder'
INIT_MODULE = 'chatcoder.core.init' # <-- 修改点 1: 定义正确的源模块
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

@pytest.fixture(scope="function")
def mock_chatflow_components():
    """
    Fixture to mock all necessary chatflow components.
    Uses patch.object to directly replace the classes imported inside chatcoder.core.chatcoder.
    Returns a dictionary of the mock instances for further configuration in tests.
    """
    with patch(f'{CHATCODER_MODULE}.FileWorkflowStateStore') as mock_store_class, \
         patch(f'{CHATCODER_MODULE}.ChatFlowEngine') as mock_engine_class:

        # 创建 mock 实例
        mock_store_instance = MagicMock()
        mock_engine_instance = MagicMock()

        # 配置类工厂返回 mock 实例
        mock_store_class.return_value = mock_store_instance
        mock_engine_class.return_value = mock_engine_instance

        # Mock 数据类/枚举 (如果需要特定行为可以配置)
        # 注意：这些也需要 patch chatcoder.core.chatcoder 中的导入
        with patch(f'{CHATCODER_MODULE}.WorkflowDefinition') as mock_definition_class, \
             patch(f'{CHATCODER_MODULE}.WorkflowInstanceState') as mock_instance_state_class, \
             patch(f'{CHATCODER_MODULE}.WorkflowInstanceStatus') as mock_instance_status_class:

            mock_workflow_definition_class = mock_definition_class
            mock_workflow_instance_state_class = mock_instance_state_class
            mock_workflow_instance_status_class = mock_instance_status_class

            yield {
                'engine_class': mock_engine_class,       # WorkflowEngine 类 Mock
                'store_class': mock_store_class,         # FileWorkflowStateStore 类 Mock
                'engine_instance': mock_engine_instance, # WorkflowEngine 的 mock 实例
                'store_instance': mock_store_instance,   # FileWorkflowStateStore 的 mock 实例
                'definition_class': mock_workflow_definition_class, # WorkflowDefinition 类 mock
                'instance_state_class': mock_workflow_instance_state_class, # WorkflowInstanceState 类 mock
                'instance_status_class': mock_workflow_instance_status_class, # WorkflowInstanceStatus 类 mock
            }

@pytest.fixture(scope="function")
def mock_chatcontext_components():
    """
    Fixture to mock all necessary chatcontext components.
    Uses patch.object to directly replace the classes imported inside chatcoder.core.chatcoder.
    Returns a dictionary of the mock instances.
    """
    with patch(f'{CHATCODER_MODULE}.ContextManager') as mock_manager_class, \
         patch(f'{CHATCODER_MODULE}.ContextRequest') as mock_request_class:

        # 创建 mock 实例
        mock_manager_instance = MagicMock()
        mock_context_request_class = mock_request_class # ContextRequest 通常是数据类

        # 配置类工厂返回 mock 实例 (ContextManager)
        mock_manager_class.return_value = mock_manager_instance

        yield {
            'manager_class': mock_manager_class,         # ContextManager 类 Mock
            'request_class': mock_context_request_class, # ContextRequest 类 Mock
            'manager_instance': mock_manager_instance,   # ContextManager 的 mock 实例
        }

@pytest.fixture(scope="function")
def mock_internal_modules():
    """
    Fixture to mock other internal ChatCoder modules if needed for specific tests.
    For example, mocking chatcoder.core.init.
    """
    with patch(f'{INIT_MODULE}.init_project') as mock_init, \
         patch(f'{INIT_MODULE}.validate_config') as mock_validate:
        yield {
            'init_project': mock_init,
            'validate_config': mock_validate
        }

@pytest.fixture(scope="function")
def chatcoder_service(
    isolated_filesystem,
    mock_chatflow_components,
    mock_chatcontext_components,
    mock_internal_modules
):
    """
    提供一个完全配置好 mock 依赖的 ChatCoder 服务实例。
    这是测试 ChatCoder 类核心逻辑的主要入口点。
    """
    # --- 关键修改：确保隔离的文件系统路径被设置到 mock store ---
    # 在 ChatCoder.__init__ 中，TASKS_DIR 被用来创建 base_path
    # 我们需要在 mock_store_instance 被创建后，但在 ChatCoder 实例化之前设置其 base_path 属性
    # 由于 mock_store_class.return_value = mock_store_instance,
    # 当 ChatCoder 执行 FileWorkflowStateStore(base_path=...) 时，
    # 实际是调用了 mock_store_class.call_args.kwargs['base_path'] 来获取参数
    # 但我们也可以直接设置 mock_store_instance 的属性，如果 ChatCoder 内部有使用的话
    # 最简单的方法是在 ChatCoder 实例化后，再设置 mock_store_instance.base_path
    # 但更符合逻辑的是，让 mock_store_class 的调用记录下参数
    temp_tasks_dir = isolated_filesystem / ".chatcoder" / "tasks"
    # 注意：这里我们不直接设置 mock_store_instance.base_path
    # 而是期望 ChatCoder 的 __init__ 调用 FileWorkflowStateStore(base_path=...) 时，
    # mock_store_class 会记录这次调用及其参数。

    # --- 导入并实例化 ChatCoder ---
    from chatcoder.core.chatcoder import ChatCoder

    # 实例化 ChatCoder，它内部会初始化并使用被 mock 的 chatflow/chatcontext 组件
    chatcoder_instance = ChatCoder()

    # --- 实例化后，我们可以检查 mock_store_class 的调用 ---
    # 这将在 test_init_success 中验证
    # mock_store_class.assert_called_once_with(base_path=str(temp_tasks_dir))
    # 但我们把验证留给测试本身
    # --- 传递 mock 实例给测试，方便进一步配置和断言 ---
    yield {
        'service': chatcoder_instance,
        'mocks': {
            'chatflow': mock_chatflow_components,
            'chatcontext': mock_chatcontext_components,
            'internal': mock_internal_modules
        },
        'temp_dir': isolated_filesystem
    }
    # Fixture 结束，mock patchers 自动停止，temp_dir 自动清理

# --- CLI 测试的特殊 Fixture ---
@pytest.fixture
def runner():
    """提供一个 Click CliRunner 实例用于测试 CLI 命令"""
    from click.testing import CliRunner
    return CliRunner()

@pytest.fixture
def mock_cli_chatcoder():
    """
    Mock the ChatCoder class specifically for CLI tests.
    This patches the import in cli.py
    """
    with patch(f'{CLI_MODULE}.ChatCoder') as mock_chatcoder_class:
        mock_instance = MagicMock()
        mock_chatcoder_class.return_value = mock_instance
        # 可以为 mock_instance 预设一些默认行为
        mock_instance.is_project_initialized.return_value = True
        yield mock_instance
    # patch 自动停止
