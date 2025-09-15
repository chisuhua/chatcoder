# chatcoder/tests/test_chatcoder.py
import unittest
from unittest.mock import patch, MagicMock, call
from pathlib import Path
import tempfile
import shutil

# --- 导入待测试的 ChatCoder 类 ---
# 假设测试文件在 chatcoder/tests/ 目录下
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from chatcoder.core.chatcoder import ChatCoder
# 假设 models.py 中的 ChangeSet 会被用到，或者用于断言返回类型
# from chatcoder.core.models import ChangeSet 

class TestChatCoder(unittest.TestCase):

    def setUp(self):
        """在每个测试方法运行前执行，设置测试环境。"""
        # 创建一个临时目录作为 storage_dir
        self.test_dir = tempfile.mkdtemp()
        self.storage_dir = Path(self.test_dir) / "test_chatflow_storage"
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # 初始化 ChatCoder 实例，使用临时目录
        # 注意：__init__ 会触发 WorkflowEngine 和 AIInteractionManager 的初始化
        # 我们需要在 patch 后再创建实例，或者在 patch 的上下文中创建
        # 这里我们先不创建，而是在需要具体 mock 的测试中创建

    def tearDown(self):
        """在每个测试方法运行后执行，清理测试环境。"""
        # 清理临时目录
        shutil.rmtree(self.test_dir, ignore_errors=True)

    @patch('chatcoder.core.chatcoder.WorkflowEngine')
    @patch('chatcoder.core.chatcoder.AIInteractionManager')
    @patch('chatcoder.core.chatcoder.TaskOrchestrator')
    def test_start_new_feature_success(self, mock_task_orchestrator_cls, mock_ai_manager_cls, mock_workflow_engine_cls):
        """测试成功启动新特性。"""
        # --- 设置 Mock 对象 ---
        mock_workflow_engine = MagicMock()
        mock_workflow_engine_cls.return_value = mock_workflow_engine
        
        mock_task_orchestrator = MagicMock()
        mock_task_orchestrator_cls.return_value = mock_task_orchestrator
        mock_task_orchestrator.generate_feature_id.return_value = "feat_test_feature"
        
        # 模拟 chatflow 的 start_workflow_instance 返回值
        mock_start_result = MagicMock()
        mock_start_result.instance_id = "wfi_test123"
        mock_start_result.initial_phase = "analyze"
        mock_workflow_engine.start_workflow_instance.return_value = mock_start_result

        # --- 执行测试 ---
        coder = ChatCoder(storage_dir=str(self.storage_dir))
        description = "Implement user authentication"
        workflow_name = "default"
        result = coder.start_new_feature(description, workflow_name)

        # --- 验证断言 ---
        # 1. 验证 TaskOrchestrator 方法被调用
        mock_task_orchestrator.generate_feature_id.assert_called_once_with(description)
        
        # 2. 验证 WorkflowEngine.start_workflow_instance 被正确调用
        # 检查调用参数 (使用 ANY 来匹配动态生成的字典和元数据)
        from unittest.mock import ANY
        mock_workflow_engine.start_workflow_instance.assert_called_once_with(
            schema_name=workflow_name,
            initial_context=ANY, # 检查是否传递了 initial_context 字典
            feature_id="feat_test_feature",
            meta=ANY # 检查是否传递了 meta 字典
        )
        # 进一步检查 initial_context 的内容
        called_kwargs = mock_workflow_engine.start_workflow_instance.call_args.kwargs
        self.assertIn("user_request", called_kwargs['initial_context'])
        self.assertEqual(called_kwargs['initial_context']['user_request'], description)
        self.assertIn("project_type", called_kwargs['initial_context'])
        # project_type 由 detector 生成，这里假设它被调用了并返回了某个值
        
        # 3. 验证返回结果
        self.assertIsInstance(result, dict)
        self.assertEqual(result["feature_id"], "feat_test_feature")
        self.assertEqual(result["description"], description)
        self.assertEqual(result["instance_id"], "wfi_test123")


    @patch('chatcoder.core.chatcoder.WorkflowEngine')
    @patch('chatcoder.utils.console.console.input') 
    def test_confirm_task_and_advance_success(self, mock_console_input, mock_workflow_engine_cls):
        """测试成功确认并推进任务。"""
        # --- 设置 Mock 对象 ---
        mock_workflow_engine = MagicMock()
        mock_workflow_engine_cls.return_value = mock_workflow_engine
        
        # 模拟 get_workflow_state 返回一个有效的状态
        mock_workflow_state = MagicMock()
        mock_workflow_state.current_phase = "analyze"
        mock_workflow_state.status.value = "running"
        mock_workflow_state.feature_id = "feat_test_feature"
        mock_workflow_engine.get_workflow_state.return_value = mock_workflow_state

        # 模拟 trigger_next_step 返回更新后的状态
        mock_updated_state = MagicMock()
        mock_updated_state.current_phase = "design"
        mock_updated_state.status.value = "running"
        mock_updated_state.feature_id = "feat_test_feature"
        mock_workflow_engine.trigger_next_step.return_value = mock_updated_state

        mock_console_input.return_value = '' # <-- 模拟用户直接按回车确认

        # --- 执行测试 ---
        coder = ChatCoder(storage_dir=str(self.storage_dir))
        instance_id = "wfi_test123"
        summary = "Analysis complete"
        # 为了简化测试，假设用户确认为 True (需要 mock console.confirm)
        result = coder.confirm_task_and_advance(instance_id, summary, user_confirmation=True)

        # --- 验证断言 ---
        # 1. 验证 get_workflow_state 被调用
        mock_workflow_engine.get_workflow_state.assert_called_once_with(instance_id)
        
        # 2. 验证 trigger_next_step 被调用 (dry_run=True 和 dry_run=False)
        expected_calls = [
            call(instance_id=instance_id, trigger_data={'summary': summary}, dry_run=True),
            call(instance_id=instance_id, trigger_data={'summary': summary}, meta={'user_confirmed': True}) 
        ]
        mock_workflow_engine.trigger_next_step.assert_has_calls(expected_calls)

        mock_console_input.assert_called_once() # <-- 验证 mock_console_input 被调用了一次
        
        # 3. 验证返回结果
        self.assertIsInstance(result, dict)
        self.assertEqual(result["next_phase"], "design")
        self.assertEqual(result["status"], "running")
        self.assertEqual(result["feature_id"], "feat_test_feature")


    @patch('chatcoder.core.chatcoder.WorkflowEngine')
    def test_generate_prompt_for_current_task_success(self, mock_workflow_engine_cls):
        """测试成功为当前任务生成提示词。"""
        # --- 设置 Mock 对象 ---
        mock_workflow_engine = MagicMock()
        mock_workflow_engine_cls.return_value = mock_workflow_engine
        
        # 模拟 get_workflow_state
        mock_workflow_state = MagicMock()
        mock_workflow_state.current_phase = "analyze"
        mock_workflow_engine.get_workflow_state.return_value = mock_workflow_state

        # --- Mock AIInteractionManager ---
        with patch('chatcoder.core.chatcoder.AIInteractionManager') as mock_ai_manager_cls:
            mock_ai_manager = MagicMock()
            mock_ai_manager_cls.return_value = mock_ai_manager
            mock_ai_manager.render_prompt_for_feature_current_task.return_value = "Generated Prompt Content"

            # --- 执行测试 ---
            coder = ChatCoder(storage_dir=str(self.storage_dir))
            instance_id = "wfi_test123"
            prompt = coder.generate_prompt_for_current_task(instance_id)

            # --- 验证断言 ---
            mock_workflow_engine.get_workflow_state.assert_called_once_with(instance_id)
            # 验证 AIInteractionManager 的方法被调用，并传入了正确的 state
            mock_ai_manager.render_prompt_for_feature_current_task.assert_called_once_with(
                instance_id=instance_id,
                workflow_state=mock_workflow_state
            )
            self.assertEqual(prompt, "Generated Prompt Content")


    @patch('chatcoder.core.chatcoder.WorkflowEngine')
    def test_get_instance_detail_status_success(self, mock_workflow_engine_cls):
        """测试成功获取实例详细状态。"""
        # --- 设置 Mock 对象 ---
        mock_workflow_engine = MagicMock()
        mock_workflow_engine_cls.return_value = mock_workflow_engine
        
        # 模拟 get_workflow_state 返回一个状态对象
        mock_workflow_state = MagicMock()
        # 模拟 asdict 的返回值
        mock_state_dict = {
            "instance_id": "wfi_test123",
            "feature_id": "feat_test_feature",
            "current_phase": "analyze",
            "status": "running"
        }
        # 注意：这里我们不能直接 mock asdict，因为它是标准库函数。
        # 更好的方法是让 mock_workflow_state 本身表现得像一个 dataclass
        # 或者在测试中 patch chatflow 的 WorkflowState.from_dict 和 asdict
        # 为了简化，我们直接让 get_workflow_state 返回一个 dict
        # 但这与实际实现不符。更严谨的做法是 mock WorkflowState 实例及其 asdict 输出
        # 让我们重新设计这个 mock
        mock_workflow_engine.get_workflow_state.return_value = mock_workflow_state
        # 我们需要 mock asdict 的行为
        mock_workflow_state_as_dict = mock_state_dict

        # --- 执行测试 ---
        coder = ChatCoder(storage_dir=str(self.storage_dir))
        instance_id = "wfi_test123"
        
        # Mock asdict
        with patch('chatcoder.core.chatcoder.asdict', return_value=mock_workflow_state_as_dict):
            status = coder.get_instance_detail_status(instance_id)

        # --- 验证断言 ---
        mock_workflow_engine.get_workflow_state.assert_called_once_with(instance_id)
        self.assertEqual(status, mock_workflow_state_as_dict)


    @patch('chatcoder.core.chatcoder.WorkflowEngine')
    def test_list_all_features_success(self, mock_workflow_engine_cls):
        """测试成功列出所有特性。"""
        # --- 设置 Mock 对象 ---
        mock_workflow_engine = MagicMock()
        mock_workflow_engine_cls.return_value = mock_workflow_engine
        # Mock state_store.list_features
        mock_workflow_engine.state_store.list_features.return_value = ["feat_1", "feat_2"]

        # --- 执行测试 ---
        coder = ChatCoder(storage_dir=str(self.storage_dir))
        features = coder.list_all_features()

        # --- 验证断言 ---
        mock_workflow_engine.state_store.list_features.assert_called_once()
        self.assertEqual(features, ["feat_1", "feat_2"])


    @patch('chatcoder.core.chatcoder.WorkflowEngine')
    def test_get_feature_instances_success(self, mock_workflow_engine_cls):
        """测试成功获取特性关联的实例。"""
        # --- 设置 Mock 对象 ---
        mock_workflow_engine = MagicMock()
        mock_workflow_engine_cls.return_value = mock_workflow_engine
        
        # Mock state_store.list_instances_by_feature
        mock_workflow_engine.state_store.list_instances_by_feature.return_value = ["wfi_1", "wfi_2"]
        
        # Mock get_workflow_status_info
        mock_status_info_1 = MagicMock()
        mock_status_info_1_dict = {"instance_id": "wfi_1", "status": "running"}
        mock_status_info_2 = MagicMock()
        mock_status_info_2_dict = {"instance_id": "wfi_2", "status": "completed"}
        
        # Mock asdict for status info objects
        with patch('chatcoder.core.chatcoder.asdict', side_effect=[mock_status_info_1_dict, mock_status_info_2_dict]):
            mock_workflow_engine.get_workflow_status_info.side_effect = [mock_status_info_1, mock_status_info_2]

            # --- 执行测试 ---
            coder = ChatCoder(storage_dir=str(self.storage_dir))
            feature_id = "feat_test"
            instances = coder.get_feature_instances(feature_id)

            # --- 验证断言 ---
            mock_workflow_engine.state_store.list_instances_by_feature.assert_called_once_with(feature_id)
            expected_calls = [call("wfi_1"), call("wfi_2")]
            mock_workflow_engine.get_workflow_status_info.assert_has_calls(expected_calls)
            self.assertEqual(len(instances), 2)
            self.assertIn(mock_status_info_1_dict, instances)
            self.assertIn(mock_status_info_2_dict, instances)


    # --- 测试错误处理 ---
    @patch('chatcoder.core.chatcoder.WorkflowEngine')
    def test_start_new_feature_failure(self, mock_workflow_engine_cls):
        """测试启动新特性时发生错误。"""
        mock_workflow_engine = MagicMock()
        mock_workflow_engine_cls.return_value = mock_workflow_engine
        mock_workflow_engine.start_workflow_instance.side_effect = Exception("Schema not found")

        coder = ChatCoder(storage_dir=str(self.storage_dir))
        
        with self.assertRaises(RuntimeError) as context:
            coder.start_new_feature("Test feature", "nonexistent_workflow")
        
        self.assertIn("Failed to start feature", str(context.exception))
        self.assertIn("Schema not found", str(context.exception))


    @patch('chatcoder.core.chatcoder.WorkflowEngine')
    def test_generate_prompt_for_current_task_not_found(self, mock_workflow_engine_cls):
        """测试为不存在的实例生成提示词。"""
        mock_workflow_engine = MagicMock()
        mock_workflow_engine_cls.return_value = mock_workflow_engine
        mock_workflow_engine.get_workflow_state.return_value = None # 模拟实例未找到

        coder = ChatCoder(storage_dir=str(self.storage_dir))
        
        with self.assertRaises(ValueError) as context:
            coder.generate_prompt_for_current_task("wfi_nonexistent")
        
        self.assertIn("wfi_nonexistent not found", str(context.exception))


if __name__ == '__main__':
    # 可以添加日志或更详细的测试运行器配置
    unittest.main()
