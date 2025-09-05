# tests/test_state.py
import pytest
import json
from pathlib import Path
# 不再直接导入旧的 state 函数，而是导入模型和服务
from chatcoder.core.models import TaskStatus
from chatcoder.core.orchestrator import TaskOrchestrator
# 如果需要测试旧的兼容性函数（如果还保留着），可以导入
# from chatcoder.core.state import generate_task_id as old_generate_task_id

def test_task_orchestrator_generate_task_id_format(task_orchestrator):
    """测试 TaskOrchestrator 任务 ID 生成格式"""
    task_id = task_orchestrator.generate_task_id()
    parts = task_id.split('_')
    assert len(parts) == 3
    assert parts[0] == 'tsk'
    assert parts[1].isdigit() # Unix timestamp should be numeric
    assert len(parts[2]) == 6 # Random suffix length

def test_task_orchestrator_generate_feature_id_basic(task_orchestrator):
    """测试 TaskOrchestrator 特性 ID 生成"""
    desc = "Implement user authentication"
    feature_id = task_orchestrator.generate_feature_id(desc)
    assert feature_id.startswith("feat_")
    # Check if key words are included (basic check)
    assert any(word in feature_id for word in ["user", "auth", "implement"])

def test_task_orchestrator_save_and_load_task_state(temp_project_dir, task_orchestrator):
    """测试 TaskOrchestrator 保存和加载任务状态"""
    task_id = "tsk_test_123456"
    template = "analyze"
    description = "Test task"
    context = {"rendered": "This is the rendered prompt"}
    feature_id = "feat_test_feature"
    phase = "analyze"
    status = TaskStatus.PENDING.value # 使用枚举值
    workflow = "default"

    task_orchestrator.save_task_state(
        task_id=task_id,
        template=template,
        description=description,
        context=context,
        feature_id=feature_id,
        phase=phase,
        status=status,
        workflow=workflow
    )

    # Check if file was created
    task_file = task_orchestrator.get_task_file_path(task_id)
    assert task_file.exists()

    # Load the state back
    loaded_data = task_orchestrator.load_task_state(task_id)
    assert loaded_data is not None
    assert loaded_data["task_id"] == task_id
    assert loaded_data["template"] == template
    assert loaded_data["description"] == description
    assert loaded_data["context"] == context
    assert loaded_data["feature_id"] == feature_id
    assert loaded_data["phase"] == phase
    assert loaded_data["status"] == status
    assert loaded_data["workflow"] == workflow
    assert "created_at" in loaded_data
    assert "created_at_str" in loaded_data

def test_task_orchestrator_load_task_state_not_found(task_orchestrator):
    """测试 TaskOrchestrator 加载不存在的任务状态"""
    loaded_data = task_orchestrator.load_task_state("tsk_nonexistent_000000")
    assert loaded_data is None

def test_task_orchestrator_list_task_states(temp_project_dir, task_orchestrator):
    """测试 TaskOrchestrator 列出任务状态"""
    # Save a couple of tasks first
    task_orchestrator.save_task_state("tsk_1", "analyze", "Task 1", {}, "feat_1", "analyze", TaskStatus.PENDING.value)
    task_orchestrator.save_task_state("tsk_2", "design", "Task 2", {}, "feat_1", "design", TaskStatus.CONFIRMED.value)
    
    tasks = task_orchestrator.list_task_states()
    assert len(tasks) == 2
    # Should be sorted by creation time, latest first. 
    task_ids = [t["task_id"] for t in tasks]
    assert "tsk_1" in task_ids
    assert "tsk_2" in task_ids
    # Check if key fields are present
    for task in tasks:
        assert "task_id" in task
        assert "template" in task
        assert "description" in task
        assert "status" in task
        assert "created_at_str" in task

# --- 可选：测试 get_latest_task ---
def test_task_orchestrator_get_latest_task(temp_project_dir, task_orchestrator):
    """测试 TaskOrchestrator 获取最新任务"""
    task_orchestrator.save_task_state("tsk_1", "analyze", "Task 1", {}, "feat_1", "analyze", TaskStatus.PENDING.value)
    # 稍微等待以确保时间戳不同 (虽然在测试中可能不是绝对必要)
    import time
    time.sleep(0.01) 
    task_orchestrator.save_task_state("tsk_2", "design", "Task 2", {}, "feat_1", "design", TaskStatus.CONFIRMED.value)
    
    latest_task = task_orchestrator.get_latest_task()
    assert latest_task is not None
    assert latest_task["task_id"] == "tsk_2"
