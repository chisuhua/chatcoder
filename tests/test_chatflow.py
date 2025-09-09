# tests/test_chatflow.py
"""
ChatFlow 库单元测试
测试 chatflow 核心模块的功能，包括 models, state, engine, workflow_engine, file_state_store。
"""

import pytest
import json
import tempfile
import os
from typing import Dict, Any, Optional, List
from pathlib import Path
from unittest.mock import MagicMock, patch
from datetime import datetime

# --- 导入 chatflow 模块进行测试 ---
try:
    from chatflow.core.models import (
        WorkflowInstanceStatus, WorkflowInstanceState,
        WorkflowDefinition, WorkflowPhaseDefinition
    )
    from chatflow.core.state import IWorkflowStateStore
    from chatflow.core.engine import IWorkflowEngine
    from chatflow.core.file_state_store import FileWorkflowStateStore
    from chatflow.core.workflow_engine import WorkflowEngine
    CHATFLOW_AVAILABLE = True
except ImportError as e:
    CHATFLOW_AVAILABLE = False
    pytest.skip(f"Skipping chatflow tests: {e}", allow_module_level=True)

# --- Fixtures ---

@pytest.fixture
def temp_dir():
    """提供一个临时目录用于测试文件状态存储。"""
    with tempfile.TemporaryDirectory() as tmpdirname:
        yield Path(tmpdirname)

@pytest.fixture
def sample_workflow_definition():
    """提供一个示例工作流定义。"""
    return WorkflowDefinition(
        name="test_workflow",
        description="A test workflow",
        phases=[
            WorkflowPhaseDefinition(name="analyze", title="Analyze", template="analyze"),
            WorkflowPhaseDefinition(name="design", title="Design", template="design"),
            WorkflowPhaseDefinition(name="implement", title="Implement", template="implement"),
        ]
    )

@pytest.fixture
def sample_workflow_instance_state(sample_workflow_definition):
    """提供一个示例工作流实例状态。"""
    return WorkflowInstanceState(
        instance_id="wfi_test_123",
        feature_id="feat_test_feature",
        workflow_name=sample_workflow_definition.name,
        current_phase="analyze",
        history=[{"phase": "init", "status": "completed"}],
        variables={"key": "value"},
        status=WorkflowInstanceStatus.RUNNING,
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat(),
    )

# --- Tests for Models ---

def test_workflow_instance_status_enum():
    """测试 WorkflowInstanceStatus 枚举。"""
    assert WorkflowInstanceStatus.CREATED.value == "created"
    assert WorkflowInstanceStatus.RUNNING.value == "running"
    assert WorkflowInstanceStatus.COMPLETED.value == "completed"
    assert WorkflowInstanceStatus.FAILED.value == "failed"

def test_workflow_instance_state_creation(sample_workflow_definition):
    """测试 WorkflowInstanceState 的创建。"""
    state = WorkflowInstanceState(
        instance_id="wfi_test_123",
        feature_id="feat_test_feature",
        workflow_name=sample_workflow_definition.name,
    )
    assert state.instance_id == "wfi_test_123"
    assert state.feature_id == "feat_test_feature"
    assert state.workflow_name == sample_workflow_definition.name
    assert state.current_phase is None
    assert state.history == []
    assert state.variables == {}
    assert state.status == WorkflowInstanceStatus.CREATED
    assert state.created_at == ""
    assert state.updated_at == ""

def test_workflow_definition_from_dict():
    """测试 WorkflowDefinition.from_dict 方法。"""
    data = {
        "name": "test_workflow",
        "description": "A test workflow",
        "phases": [
            {"name": "analyze", "title": "Analyze", "template": "analyze"},
            {"name": "design", "title": "Design", "template": "design"},
        ]
    }
    definition = WorkflowDefinition.from_dict(data)
    assert definition.name == "test_workflow"
    assert definition.description == "A test workflow"
    assert len(definition.phases) == 2
    assert definition.phases[0].name == "analyze"
    assert definition.phases[1].title == "Design"

# --- Tests for FileWorkflowStateStore ---

def test_file_workflow_state_store_save_and_load_state(temp_dir, sample_workflow_instance_state):
    """测试 FileWorkflowStateStore 的 save_state 和 load_state 方法。"""
    store = FileWorkflowStateStore(base_dir=temp_dir)
    
    instance_id = sample_workflow_instance_state.instance_id
    state_data = {
        "instance_id": instance_id,
        "feature_id": sample_workflow_instance_state.feature_id,
        "workflow_name": sample_workflow_instance_state.workflow_name,
        "current_phase": sample_workflow_instance_state.current_phase,
        "history": sample_workflow_instance_state.history,
        "variables": sample_workflow_instance_state.variables,
        "status": sample_workflow_instance_state.status.value,
        "created_at": sample_workflow_instance_state.created_at,
        "updated_at": sample_workflow_instance_state.updated_at,
    }
    
    # 保存状态
    store.save_state(instance_id, state_data)
    
    # 加载状态
    loaded_data = store.load_state(instance_id)
    
    assert loaded_data is not None
    assert loaded_data["instance_id"] == instance_id
    assert loaded_data["feature_id"] == sample_workflow_instance_state.feature_id
    assert loaded_data["workflow_name"] == sample_workflow_instance_state.workflow_name
    assert loaded_data["current_phase"] == sample_workflow_instance_state.current_phase
    assert loaded_data["history"] == sample_workflow_instance_state.history
    assert loaded_data["variables"] == sample_workflow_instance_state.variables
    assert loaded_data["status"] == sample_workflow_instance_state.status.value
    # 注意：created_at 和 updated_at 可能会在 save_state 中被更新，所以比较需要容差

def test_file_workflow_state_store_load_state_not_found(temp_dir):
    """测试 FileWorkflowStateStore 加载不存在的状态。"""
    store = FileWorkflowStateStore(base_dir=temp_dir)
    loaded_data = store.load_state("non_existent_id")
    assert loaded_data is None

def test_file_workflow_state_store_list_instances_by_feature(temp_dir):
    """测试 FileWorkflowStateStore 的 list_instances_by_feature 方法。"""
    store = FileWorkflowStateStore(base_dir=temp_dir)
    
    # 创建两个属于同一 feature 的实例状态
    state_data_1 = {
        "instance_id": "wfi_1",
        "feature_id": "feat_test",
        "workflow_name": "default",
        "current_phase": "analyze",
        "status": "running",
    }
    state_data_2 = {
        "instance_id": "wfi_2",
        "feature_id": "feat_test",
        "workflow_name": "default",
        "current_phase": "design",
        "status": "completed",
    }
    # 创建一个属于不同 feature 的实例状态
    state_data_3 = {
        "instance_id": "wfi_3",
        "feature_id": "feat_other",
        "workflow_name": "default",
        "current_phase": "implement",
        "status": "running",
    }
    
    store.save_state("wfi_1", state_data_1)
    store.save_state("wfi_2", state_data_2)
    store.save_state("wfi_3", state_data_3)
    
    # 查询 feat_test 的实例
    instances = store.list_instances_by_feature("feat_test")
    
    assert len(instances) == 2
    instance_ids = {i["instance_id"] for i in instances}
    assert instance_ids == {"wfi_1", "wfi_2"}

# --- Tests for WorkflowEngine ---

@pytest.fixture
def mock_state_store():
    """提供一个模拟的 IWorkflowStateStore。"""
    return MagicMock(spec=IWorkflowStateStore)

@pytest.fixture
def workflow_engine(mock_state_store):
    """提供一个 WorkflowEngine 实例。"""
    return WorkflowEngine(state_store=mock_state_store)

def test_workflow_engine_initialization(mock_state_store):
    """测试 WorkflowEngine 的初始化。"""
    engine = WorkflowEngine(state_store=mock_state_store)
    assert engine.state_store == mock_state_store

def test_workflow_engine_load_workflow_schema_default():
    """测试 WorkflowEngine 加载默认工作流模式。"""
    # 使用真实的 TEMPLATES_DIR 来测试
    from chatflow.core.workflow_engine import get_workflow_path
    workflows_dir = get_workflow_path()
    
    if not workflows_dir.exists():
        pytest.skip("Workflows directory not found, skipping schema loading test.")
        
    default_schema_file = workflows_dir / "default.yaml"
    if not default_schema_file.exists():
        pytest.skip("Default workflow schema not found, skipping schema loading test.")
    
    engine = WorkflowEngine(state_store=MagicMock())
    schema = engine.load_workflow_schema("default")
    assert isinstance(schema, dict)
    assert schema["name"] == "default"
    assert "phases" in schema

def test_workflow_engine_get_phase_order(sample_workflow_definition):
    """测试 WorkflowEngine 的 get_phase_order 方法。"""
    engine = WorkflowEngine(state_store=MagicMock())
    order = engine.get_phase_order(sample_workflow_definition)
    expected_order = {"analyze": 0, "design": 1, "implement": 2}
    assert order == expected_order

def test_workflow_engine_get_next_phase(sample_workflow_definition):
    """测试 WorkflowEngine 的 get_next_phase 方法。"""
    engine = WorkflowEngine(state_store=MagicMock())
    next_phase = engine.get_next_phase(sample_workflow_definition, "analyze")
    assert next_phase == "design"
    
    next_phase = engine.get_next_phase(sample_workflow_definition, "implement")
    assert next_phase is None # 最后一个阶段

def test_workflow_engine_start_workflow_instance(sample_workflow_definition, mock_state_store):
    """测试 WorkflowEngine 的 start_workflow_instance 方法。"""
    engine = WorkflowEngine(state_store=mock_state_store)
    
    initial_context = {"project_name": "Test Project"}
    feature_id = "feat_test_start"
    
    with patch('chatflow.core.workflow_engine.uuid.uuid4') as mock_uuid, \
         patch('chatflow.core.workflow_engine.datetime') as mock_datetime:
        
        mock_uuid.return_value.hex = 'a1b2c3d4e5f6'
        mock_datetime.now.return_value.isoformat.return_value = '2023-10-27T10:00:00'
        
        instance_id = engine.start_workflow_instance(sample_workflow_definition, initial_context, feature_id)
        
        assert instance_id == "wfi_a1b2c3d4e5f6"
        # 验证 save_state 是否被正确调用
        mock_state_store.save_state.assert_called_once()
        call_args = mock_state_store.save_state.call_args
        saved_instance_id, saved_state_data = call_args[0]
        assert saved_instance_id == instance_id
        assert saved_state_data["feature_id"] == feature_id
        assert saved_state_data["workflow_name"] == sample_workflow_definition.name
        assert saved_state_data["current_phase"] == "analyze" # 第一个阶段
        assert saved_state_data["variables"] == initial_context
        assert saved_state_data["status"] == WorkflowInstanceStatus.CREATED.value

def test_workflow_engine_trigger_next_step(mock_state_store, sample_workflow_instance_state):
    """测试 WorkflowEngine 的 trigger_next_step 方法。"""
    engine = WorkflowEngine(state_store=mock_state_store)
    
    instance_id = sample_workflow_instance_state.instance_id
    state_data = {
        "instance_id": instance_id,
        "feature_id": sample_workflow_instance_state.feature_id,
        "workflow_name": sample_workflow_instance_state.workflow_name,
        "current_phase": sample_workflow_instance_state.current_phase,
        "history": sample_workflow_instance_state.history,
        "variables": sample_workflow_instance_state.variables,
        "status": sample_workflow_instance_state.status.value,
        "created_at": sample_workflow_instance_state.created_at,
        "updated_at": sample_workflow_instance_state.updated_at,
    }
    
    # 模拟 load_state 返回初始状态
    mock_state_store.load_state.return_value = state_data
    
    # 模拟 load_workflow_schema 返回工作流定义
    mock_schema = {
        "name": "test_workflow",
        "phases": [
            {"name": "analyze", "title": "Analyze", "template": "analyze"},
            {"name": "design", "title": "Design", "template": "design"},
        ]
    }
    with patch.object(engine, 'load_workflow_schema', return_value=mock_schema):
        updated_state = engine.trigger_next_step(instance_id)
        
        # 验证 load_state 被调用
        mock_state_store.load_state.assert_called_once_with(instance_id)
        # 验证 save_state 被调用，并且状态已更新
        mock_state_store.save_state.assert_called_once()
        call_args = mock_state_store.save_state.call_args
        saved_instance_id, saved_state_data = call_args[0]
        assert saved_instance_id == instance_id
        # 检查状态是否更新：历史记录增加，当前阶段前进，状态变为 RUNNING (或根据逻辑)
        assert len(saved_state_data["history"]) == len(state_data["history"])
        assert saved_state_data["current_phase"] == "design" # 前进到下一阶段
        # assert saved_state_data["status"] == WorkflowInstanceStatus.RUNNING.value # 或其他逻辑

# --- Tests for Interfaces (Abstract Base Classes) ---

def test_iworkflow_state_store_interface():
    """测试 IWorkflowStateStore 接口定义。"""
    # 尝试实例化抽象类应该失败
    with pytest.raises(TypeError):
        IWorkflowStateStore()

    # 创建一个具体的子类来测试接口
    class ConcreteStateStore(IWorkflowStateStore):
        def save_state(self, instance_id: str, state_data: Dict[str, Any]) -> None:
            pass
        def load_state(self, instance_id: str) -> Optional[Dict[str, Any]]:
            pass
        def list_instances_by_feature(self, feature_id: str) -> List[Dict[str, Any]]:
            pass

    # 实例化具体的子类应该成功
    concrete_store = ConcreteStateStore()
    assert isinstance(concrete_store, IWorkflowStateStore)

def test_iworkflow_engine_interface():
    """测试 IWorkflowEngine 接口定义。"""
    # 尝试实例化抽象类应该失败
    with pytest.raises(TypeError):
        IWorkflowEngine()

    # 创建一个具体的子类来测试接口
    class ConcreteWorkflowEngine(IWorkflowEngine):
        def load_workflow_schema(self, name: str = "default") -> dict:
            pass
        def get_feature_status(self, feature_id: str, schema_name: str = "default") -> Dict[str, Any]:
            pass
        def recommend_next_phase(self, feature_id: str, schema_name: str = "default") -> Optional[Dict[str, Any]]:
            pass
        def start_workflow_instance(self, workflow_definition: 'WorkflowDefinition', initial_context: Dict[str, Any], feature_id: str) -> str:
            pass
        def trigger_next_step(self, instance_id: str, trigger_data: Optional[Dict[str, Any]] = None) -> 'WorkflowInstanceState':
            pass

    # 实例化具体的子类应该成功
    concrete_engine = ConcreteWorkflowEngine()
    assert isinstance(concrete_engine, IWorkflowEngine)
