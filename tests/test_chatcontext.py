# tests/test_chatcontext.py
import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# 将项目根目录添加到 sys.path 以便导入 chatcontext 包
# 假设测试文件位于项目根目录下的 tests/ 文件夹中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# --- 导入待测试的 chatcontext 模块 ---
from chatcontext.core.models import ContextRequest, ProvidedContext, FinalContext, ContextType
from chatcontext.core.provider import IContextProvider
from chatcontext.core.manager import ContextManager

# 导入示例 Provider (如果已实现)
# from chatcontext.providers.project_info import ProjectInfoProvider
# from chatcontext.providers.core_files import CoreFilesProvider


class TestChatContextModels(unittest.TestCase):

    def test_context_request_creation(self):
        """测试 ContextRequest 模型创建"""
        request = ContextRequest(
            workflow_instance_id="wfi_abc123",  # 使用修改后的字段名
            feature_id="feat_test",
            current_phase="analyze",
            task_description="Test task"
        )
        self.assertEqual(request.workflow_instance_id, "wfi_abc123")
        self.assertEqual(request.feature_id, "feat_test")
        self.assertEqual(request.current_phase, "analyze")
        self.assertEqual(request.task_description, "Test task")
        # 测试默认值
        self.assertIsNone(request.automation_level)
        self.assertFalse(request.is_preview)

    def test_provided_context_creation(self):
        """测试 ProvidedContext 模型创建"""
        content = {"key": "value"}
        ctx = ProvidedContext(
            content=content,
            context_type=ContextType.INFORMATIONAL,
            provider_name="TestProvider"
        )
        self.assertEqual(ctx.content, content)
        self.assertEqual(ctx.context_type, ContextType.INFORMATIONAL)
        self.assertEqual(ctx.provider_name, "TestProvider")
        # 测试 v1.1 默认值
        self.assertEqual(ctx.relevance_score, 1.0)
        self.assertIsNone(ctx.summary)
        self.assertIsNone(ctx.size_estimate)

    def test_final_context_creation(self):
        """测试 FinalContext 模型创建"""
        merged_data = {"final": "data"}
        diagnostics = [{"provider": "TestProvider", "status": "success"}]
        fc = FinalContext(
            merged_data=merged_data,
            provider_diagnostics=diagnostics,
            generation_time=0.5,
            total_size=100
        )
        self.assertEqual(fc.merged_data, merged_data)
        self.assertEqual(fc.provider_diagnostics, diagnostics)
        self.assertEqual(fc.generation_time, 0.5)
        self.assertEqual(fc.total_size, 100)
        # 测试默认值
        self.assertEqual(fc.suggestions, [])


class TestChatContextProvider(unittest.TestCase):

    def test_abstract_provider_cannot_instantiate(self):
        """测试抽象 Provider 无法实例化"""
        with self.assertRaises(TypeError):
            # 直接尝试实例化抽象基类应该失败
            IContextProvider() # type: ignore

    # 注意：如果提供了具体的 Provider 实现（如 ProjectInfoProvider），
    # 可以在这里添加测试它们的实例化和默认方法行为的测试用例。
    # 例如：
    # def test_concrete_provider_instantiation(self):
    #     """测试具体 Provider 可以实例化并具有默认方法"""
    #     # 这需要实际的 Provider 实现已完成
    #     # provider = ProjectInfoProvider()
    #     # self.assertEqual(provider.name, "ProjectInfoProvider")
    #     # self.assertEqual(provider.get_priority(ContextRequest(...)), 90)
    #     # ... 测试其他默认方法
    #     pass


class TestChatContextManager(unittest.TestCase):

    def setUp(self):
        """在每个测试前设置"""
        self.manager = ContextManager()

    def test_register_provider(self):
        """测试注册 Provider"""
        # 创建一个模拟的 Provider 实例
        mock_provider = MagicMock()
        mock_provider.name = "MockProvider"
        
        self.manager.register_provider(mock_provider)
        
        # 检查 provider 是否被添加到内部列表中
        # 注意：_providers 是私有属性，直接访问可能不被推荐，
        # 但在单元测试中为了验证内部状态是可接受的。
        self.assertIn(mock_provider, self.manager._providers)

    def test_get_context_with_no_providers(self):
        """测试没有 Provider 时的上下文生成"""
        request = ContextRequest(
            workflow_instance_id="wfi_empty",
            feature_id="feat_empty",
            current_phase="start",
            task_description="No providers test"
        )
        result = self.manager.get_context(request)
        
        # 验证返回了 FinalContext 对象
        self.assertIsInstance(result, FinalContext)
        # 验证合并数据为空
        self.assertEqual(result.merged_data, {})
        # 验证总大小为0
        self.assertEqual(result.total_size, 0)
        # 验证生成时间非负
        self.assertGreaterEqual(result.generation_time, 0)
        # 应该没有诊断信息（因为没有 Provider 被调用）
        self.assertEqual(len(result.provider_diagnostics), 0)

    def test_get_context_with_successful_provider(self):
        """测试成功 Provider 的上下文生成"""
        # 创建一个 Mock Provider
        mock_provider = MagicMock()
        mock_provider.name = "SuccessfulMockProvider"
        # Mock v1.1 的可选方法
        mock_provider.get_priority.return_value = 75
        mock_provider.can_provide.return_value = True
        mock_provider.get_supported_types.return_value = [ContextType.INFORMATIONAL]
        mock_provider.get_supported_project_types.return_value = ['*']

        # Mock provide 方法返回 ProvidedContext
        mock_context = ProvidedContext(
            content={"mock_key": "mock_value"},
            context_type=ContextType.INFORMATIONAL,
            provider_name="SuccessfulMockProvider",
            relevance_score=0.8,
            size_estimate=50
        )
        mock_provider.provide.return_value = [mock_context]

        self.manager.register_provider(mock_provider)

        request = ContextRequest(
            workflow_instance_id="wfi_success",
            feature_id="feat_success",
            current_phase="process",
            task_description="Successful provider test"
        )
        result = self.manager.get_context(request)

        # 验证 Mock 方法被调用
        mock_provider.can_provide.assert_called_once_with(request)
        # 注意：get_priority 是否在 manager 内部调用取决于具体实现
        # mock_provider.get_priority.assert_called_once_with(request)
        mock_provider.provide.assert_called_once_with(request)

        # 验证结果
        self.assertIsInstance(result, FinalContext)
        self.assertIn("mock_key", result.merged_data)
        self.assertEqual(result.merged_data["mock_key"], "mock_value")
        self.assertGreater(result.total_size, 0) # 应该累加 size_estimate
        self.assertGreaterEqual(result.generation_time, 0)
        
        # 验证诊断信息
        self.assertEqual(len(result.provider_diagnostics), 1)
        diag = result.provider_diagnostics[0]
        self.assertEqual(diag["provider"], "SuccessfulMockProvider")
        self.assertEqual(diag["status"], "success")
        self.assertGreaterEqual(diag["time_taken"], 0)

    def test_get_context_with_failing_provider(self):
        """测试失败 Provider 的错误隔离"""
        # 成功的 Provider
        mock_provider_ok = MagicMock()
        mock_provider_ok.name = "OKProvider"
        mock_provider_ok.can_provide.return_value = True
        mock_provider_ok.get_priority.return_value = 50 # 可以设置优先级
        mock_provider_ok.provide.return_value = [ProvidedContext(
            content={"ok": "data"}, context_type=ContextType.INFORMATIONAL, provider_name="OKProvider"
        )]

        # 失败的 Provider
        mock_provider_fail = MagicMock()
        mock_provider_fail.name = "FailProvider"
        mock_provider_fail.can_provide.return_value = True
        mock_provider_fail.get_priority.return_value = 40
        # 模拟 provide 方法抛出异常
        mock_provider_fail.provide.side_effect = Exception("Provider failed!")

        self.manager.register_provider(mock_provider_ok)
        self.manager.register_provider(mock_provider_fail)

        request = ContextRequest(
            workflow_instance_id="wfi_fail",
            feature_id="feat_fail",
            current_phase="process",
            task_description="Failing provider test"
        )
        result = self.manager.get_context(request)

        # 验证两个 Provider 的 can_provide 都被调用
        mock_provider_ok.can_provide.assert_called_once_with(request)
        mock_provider_fail.can_provide.assert_called_once_with(request)

        # 验证成功的 Provider 被调用
        mock_provider_ok.provide.assert_called_once_with(request)
        # 验证失败的 Provider 被调用并抛出异常
        mock_provider_fail.provide.assert_called_once_with(request)

        # 验证结果：成功 Provider 的数据应该在
        self.assertIn("ok", result.merged_data)
        self.assertEqual(result.merged_data["ok"], "data")
        
        # 验证诊断信息：两个 Provider 都应该有记录
        # 找到失败的诊断
        fail_diag = next((d for d in result.provider_diagnostics if d["provider"] == "FailProvider"), None)
        self.assertIsNotNone(fail_diag, "Diagnostics for failed provider should be present.")
        self.assertEqual(fail_diag["status"], "error")
        self.assertIn("Provider failed!", fail_diag["error"])

    def test_provider_filtering_and_sorting(self):
        """测试 Provider 的筛选和排序 (v1.1)"""
        # 注意：这个测试的有效性取决于 ContextManager 内部是否实现了
        # 基于 can_provide 和 get_priority 的筛选与排序逻辑。
        # 当前提供的 manager.py 框架代码中包含了这部分逻辑的占位符。

        # Provider 1: 优先级低, 可以提供
        mock_provider_low_prio = MagicMock()
        mock_provider_low_prio.name = "LowPrioProvider"
        mock_provider_low_prio.get_priority.return_value = 20
        mock_provider_low_prio.can_provide.return_value = True
        mock_provider_low_prio.provide.return_value = [ProvidedContext(
            content={"low": "prio"}, context_type=ContextType.INFORMATIONAL, provider_name="LowPrioProvider"
        )]

        # Provider 2: 优先级高, 可以提供
        mock_provider_high_prio = MagicMock()
        mock_provider_high_prio.name = "HighPrioProvider"
        mock_provider_high_prio.get_priority.return_value = 80
        mock_provider_high_prio.can_provide.return_value = True
        mock_provider_high_prio.provide.return_value = [ProvidedContext(
            content={"high": "prio"}, context_type=ContextType.INFORMATIONAL, provider_name="HighPrioProvider"
        )]

        # Provider 3: 优先级中, 不能提供
        mock_provider_cannot_provide = MagicMock()
        mock_provider_cannot_provide.name = "CannotProvideProvider"
        mock_provider_cannot_provide.can_provide.return_value = False # 关键：不能提供
        # 不需要 mock provide，因为它不应该被调用

        self.manager.register_provider(mock_provider_low_prio)
        self.manager.register_provider(mock_provider_high_prio)
        self.manager.register_provider(mock_provider_cannot_provide)

        request = ContextRequest(
            workflow_instance_id="wfi_sort",
            feature_id="feat_sort",
            current_phase="process",
            task_description="Sorting test"
        )
        result = self.manager.get_context(request)

        # 验证 cannot_provide 的 Provider 的 provide 没有被调用
        mock_provider_cannot_provide.provide.assert_not_called()
        
        # 验证其他两个 Provider 的 provide 被调用了
        # 调用顺序取决于 manager 的具体实现（是否按优先级排序后调用）
        mock_provider_low_prio.provide.assert_called_once()
        mock_provider_high_prio.provide.assert_called_once()

        # 验证合并结果（简单合并逻辑下，后调用的会覆盖同名 key）
        # 由于 manager 的合并逻辑未指定，我们只验证数据存在
        self.assertIn("high", result.merged_data)
        self.assertIn("low", result.merged_data)

        # 验证诊断信息包含所有尝试过的 Provider (取决于 manager 实现)
        # 至少应包含成功和失败的
        diag_names = [d["provider"] for d in result.provider_diagnostics]
        self.assertIn("HighPrioProvider", diag_names)
        self.assertIn("LowPrioProvider", diag_names)
        # CannotProvideProvider 是否在诊断中取决于 manager 是否记录被过滤的 Provider


# --- 运行测试 ---
if __name__ == '__main__':
    unittest.main()
