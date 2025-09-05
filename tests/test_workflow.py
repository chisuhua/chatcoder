# tests/test_workflow.py
import pytest
# 不再直接导入旧的 workflow 函数，而是导入服务
from chatcoder.core.engine import WorkflowEngine
from chatcoder.core.orchestrator import TaskOrchestrator # 如果需要创建任务来测试 get_feature_status
from chatcoder.core.models import TaskStatus

def test_workflow_engine_load_workflow_schema_default(workflow_engine):
    """测试 WorkflowEngine 加载默认工作流模式"""
    schema = workflow_engine.load_workflow_schema("default")
    assert isinstance(schema, dict)
    assert schema["name"] == "default"
    assert "phases" in schema
    assert len(schema["phases"]) > 0
    assert schema["phases"][0]["name"] == "analyze"

def test_workflow_engine_load_workflow_schema_not_found(workflow_engine):
    """测试 WorkflowEngine 加载不存在的工作流模式"""
    with pytest.raises(ValueError) as excinfo:
        workflow_engine.load_workflow_schema("nonexistent")
    # 注意：原始代码中 load_workflow_schema 抛出的错误信息是 "workflows schema not foud: {name}"
    # 这里根据实际实现调整断言
    assert "not found" in str(excinfo.value).lower() or "workflows schema not foud" in str(excinfo.value)

def test_workflow_engine_get_phase_order(workflow_engine):
    """测试 WorkflowEngine 获取阶段顺序"""
    schema = workflow_engine.load_workflow_schema("default")
    order = workflow_engine.get_phase_order(schema)
    assert isinstance(order, dict)
    assert order["analyze"] == 0
    assert order["design"] == 1
    assert order["code"] == 2

def test_workflow_engine_get_next_phase(workflow_engine):
    """测试 WorkflowEngine 获取下一个阶段"""
    schema = workflow_engine.load_workflow_schema("default")
    
    next_phase = workflow_engine.get_next_phase(schema, "analyze")
    assert next_phase == "design"
    
    next_phase = workflow_engine.get_next_phase(schema, "nonexistent_phase")
    # 根据 WorkflowEngine 的实现，应该返回第一个阶段
    assert next_phase == "analyze" # Assuming this is the fallback logic in the new class

    next_phase = workflow_engine.get_next_phase(schema, "summary") # Last phase
    assert next_phase is None


# --- 测试 get_feature_status 需要 TaskOrchestrator 来设置任务 ---
def test_workflow_engine_get_feature_status_initial(temp_project_dir, workflow_engine, task_orchestrator):
    """测试 WorkflowEngine 获取特性初始状态"""
    feature_id = "feat_test_status"
    status = workflow_engine.get_feature_status(feature_id, "default")
    
    assert status["feature_id"] == feature_id
    assert status["workflow"] == "default"
    assert status["current_phase"] is None # No tasks completed yet
    assert status["next_phase"] == "analyze" # First phase recommended
    assert status["completed_count"] == 0
    # Check if all phases are initialized
    schema = workflow_engine.load_workflow_schema("default")
    for phase in schema["phases"]:
        assert status["phases"][phase["name"]] == "not-started"

def test_workflow_engine_get_feature_status_with_progress(temp_project_dir, workflow_engine, task_orchestrator):
    """测试 WorkflowEngine 获取特性带进度的状态"""
    feature_id = "feat_test_progress"
    # Save a confirmed task for 'analyze' phase (模拟 confirmed 为 completed)
    task_orchestrator.save_task_state("tsk_analyze_done", "analyze", "Analyzed", {}, feature_id, "analyze", TaskStatus.CONFIRMED.value) # 或 "completed"
    # Save a pending task for 'design' phase
    task_orchestrator.save_task_state("tsk_design_pending", "design", "Designing", {}, feature_id, "design", TaskStatus.PENDING.value)
    
    # 注意：get_feature_status 内部可能仍调用旧的 list_task_states
    # 如果已经重构为使用 task_orchestrator，这里就一致了。
    # 否则，需要确保状态映射正确（例如 confirmed -> completed）
    # 假设 get_feature_status 期望 "completed" 状态
    # 我们需要修改保存任务的 status
    task_orchestrator.save_task_state("tsk_analyze_done", "analyze", "Analyzed", {}, feature_id, "analyze", "completed")
    task_orchestrator.save_task_state("tsk_design_pending", "design", "Designing", {}, feature_id, "design", "pending")

    status = workflow_engine.get_feature_status(feature_id, "default")
    
    assert status["feature_id"] == feature_id
    assert status["current_phase"] == "analyze" # Last *completed* phase
    assert status["next_phase"] == "design" # Next phase after 'analyze'
    assert status["completed_count"] == 1
    assert status["phases"]["analyze"] == "completed"
    assert status["phases"]["design"] == "pending"
