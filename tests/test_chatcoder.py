# chatcoder/tests/test_chatcoder.py
"""
ChatCoder 核心服务单元测试
"""

import pytest
from unittest.mock import call, MagicMock

# --- 导入被测试的模块 ---
# 通过 conftest.py 的 fixtures 来管理依赖

class TestChatCoder:
    """测试 ChatCoder 核心服务类"""

    # --- 测试初始化 ---
    def test_init_success(self, chatcoder_service):
        """测试 ChatCoder 成功初始化"""
        service = chatcoder_service['service']
        mocks = chatcoder_service['mocks']
        temp_dir = chatcoder_service['temp_dir']

        expected_base_path = str((temp_dir / ".chatcoder" / "tasks").resolve())
        mocks['chatflow']['store_class'].assert_called_once_with(base_path=expected_base_path)
        expected_state_store_mock = mocks['chatflow']['store_instance']
        mocks['chatflow']['engine_class'].assert_called_once_with(state_store=expected_state_store_mock) # <-- 修改这里

        mocks['chatcontext']['manager_class'].assert_called_once()

        assert service.workflow_engine == mocks['chatflow']['engine_instance']
        assert service.state_store == mocks['chatflow']['store_instance']
        assert service.context_manager == mocks['chatcontext']['manager_instance']
        assert service.ai_manager is not None
        assert service.task_orchestrator is not None

    # --- 测试 start_new_feature ---
    def test_start_new_feature_success(self, chatcoder_service):
        """测试成功启动新特性"""
        service = chatcoder_service['service']
        mocks = chatcoder_service['mocks']
        temp_dir = chatcoder_service['temp_dir']
        
        description = "实现用户登录功能"
        workflow_name = "default"
        
        # 模拟 chatflow 的行为
        mock_schema = MagicMock()
        mock_schema.phases = [MagicMock(name="analyze", template="analyze")]
        mocks['chatflow']['engine_instance'].load_workflow_schema.return_value = mock_schema
        
        # 模拟生成的 feature_id 和 instance_id
        expected_feature_id = "feat_user_login"
        expected_instance_id = "tsk_12345"
        
        # 配置 TaskOrchestrator 的 mock (如果直接测试 TaskOrchestrator, 这里会是真实的调用)
        service.task_orchestrator.generate_feature_id = MagicMock(return_value=expected_feature_id)
        mocks['chatflow']['engine_instance'].start_workflow_instance.return_value = expected_instance_id

        # 调用被测试方法
        result = service.start_new_feature(description, workflow_name)

        # 验证结果
        assert result["feature_id"] == expected_feature_id
        assert result["description"] == description

        # 验证 mock 调用
        mocks['chatflow']['engine_instance'].load_workflow_schema.assert_called_once_with(workflow_name)
        service.task_orchestrator.generate_feature_id.assert_called_once_with(description)
        mocks['chatflow']['engine_instance'].start_workflow_instance.assert_called_once()
        call_args = mocks['chatflow']['engine_instance'].start_workflow_instance.call_args
        assert call_args.kwargs['feature_id'] == expected_feature_id
        assert call_args.kwargs['workflow_definition'] == mock_schema
        assert "feature_description" in call_args.kwargs['initial_context']

    def test_start_new_feature_invalid_workflow(self, chatcoder_service):
        """测试启动新特性时工作流无效"""
        service = chatcoder_service['service']
        mocks = chatcoder_service['mocks']
        
        description = "实现用户登录功能"
        workflow_name = "nonexistent"
        
        # 模拟 chatflow 抛出异常
        mocks['chatflow']['engine_instance'].load_workflow_schema.side_effect = ValueError("Workflows schema not found")

        with pytest.raises(RuntimeError) as exc_info:
            service.start_new_feature(description, workflow_name)

        assert "Failed to start feature" in str(exc_info.value)

    # --- 测试 generate_prompt_for_current_task ---
    def test_generate_prompt_for_current_task_success(self, chatcoder_service):
        """测试成功为当前任务生成提示词"""
        service = chatcoder_service['service']
        mocks = chatcoder_service['mocks']
        
        feature_id = "feat_test_123"
        
        # 模拟 chatflow 找到活动任务
        mock_task_state_dict = {
            "instance_id": "tsk_67890",
            "feature_id": feature_id,
            "current_phase": "design",
            "variables": {
                "chatcoder_data": {
                    "description": "设计登录页面",
                    "template": "design"
                }
            },
            "status": "RUNNING" # 假设 chatflow 的状态值
        }
        mocks['chatflow']['store_instance'].load_state.return_value = mock_task_state_dict
        
        # 模拟 AIInteractionManager 的行为
        expected_prompt = "这是为设计阶段生成的 AI 提示词..."
        service.ai_manager.render_prompt_for_feature_current_task = MagicMock(return_value=expected_prompt)

        # 调用被测试方法
        prompt = service.generate_prompt_for_current_task(feature_id)

        # 验证结果
        assert prompt == expected_prompt
        
        # 验证 mock 调用
        # load_state 的调用由 AIInteractionManager 内部处理或通过查找逻辑，这里验证 AIManager 被调用
        service.ai_manager.render_prompt_for_feature_current_task.assert_called_once_with(feature_id=feature_id)

    # --- 测试 confirm_task_and_advance ---
    def test_confirm_task_and_advance_success_with_next_phase(self, chatcoder_service):
        """测试成功确认任务并有推荐的下一阶段"""
        service = chatcoder_service['service']
        mocks = chatcoder_service['mocks']
        
        feature_id = "feat_test_789"
        summary = "已完成登录页面设计"
        
        # 模拟 chatflow 找到当前任务 ID
        current_task_id = "tsk_11111"
        mocks['chatflow']['engine_instance'].get_current_task_id_for_feature.return_value = current_task_id
        
        # 模拟 chatflow trigger_next_step 的行为
        mocks['chatflow']['engine_instance'].trigger_next_step.return_value = MagicMock()
        
        # 模拟 chatflow recommend_next_phase 的行为
        expected_next_phase = "implement"
        expected_reason = "Standard workflow progression"
        mock_recommendation = {
            "phase": expected_next_phase,
            "reason": expected_reason,
            "source": "standard"
        }
        mocks['chatflow']['engine_instance'].recommend_next_phase.return_value = mock_recommendation

        # 调用被测试方法
        result = service.confirm_task_and_advance(feature_id, summary)

        # 验证结果
        assert result is not None
        assert result["next_phase"] == expected_next_phase
        assert result["reason"] == expected_reason
        assert result["feature_id"] == feature_id
        
        # 验证 mock 调用
        mocks['chatflow']['engine_instance'].get_current_task_id_for_feature.assert_called_once_with(feature_id)
        mocks['chatflow']['engine_instance'].trigger_next_step.assert_called_once_with(current_task_id, trigger_data={"summary": summary})
        mocks['chatflow']['engine_instance'].recommend_next_phase.assert_called_once_with(feature_id)

    # --- 测试 get_all_features_status ---
    def test_get_all_features_status_success(self, chatcoder_service):
        """测试成功获取所有特性状态"""
        service = chatcoder_service['service']
        mocks = chatcoder_service['mocks']
        
        # 模拟 chatflow 返回所有 feature_id
        feature_ids = ["feat_1", "feat_2"]
        mocks['chatflow']['engine_instance'].list_all_feature_ids.return_value = feature_ids
        
        # 模拟 chatflow 为每个 feature_id 返回详细状态
        mocks['chatflow']['engine_instance'].get_feature_status.side_effect = [
            {"feature_id": "feat_1", "completed_count": 1, "total_count": 2, "description": "功能1"},
            {"feature_id": "feat_2", "completed_count": 2, "total_count": 2, "description": "功能2"},
        ]

        statuses = service.get_all_features_status()

        assert len(statuses) == 2
        # 检查返回的摘要信息 (逻辑在 ChatCoder 内部实现)
        assert any(s["feature_id"] == "feat_1" and s["status"] == "in_progress" for s in statuses)
        assert any(s["feature_id"] == "feat_2" and s["status"] == "completed" for s in statuses)
        
        mocks['chatflow']['engine_instance'].list_all_feature_ids.assert_called_once()
        expected_calls = [call("feat_1", "default"), call("feat_2", "default")]
        mocks['chatflow']['engine_instance'].get_feature_status.assert_has_calls(expected_calls)

    # --- 其他测试可以类似添加 ---
    # ... (为其他方法添加测试)
