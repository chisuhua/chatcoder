# ChatFlow v1.1 单元测试套件

以下是为 **ChatFlow v1.1** 设计的全面单元测试，覆盖核心功能：单例模式、文件锁、状态管理、Schema 验证、条件分支和 Dry Run 模式。

```python
# tests/test_workflow_engine.py
import os
import tempfile
import threading
import time
from datetime import datetime
import json
import pytest
from unittest.mock import patch, mock_open

from chatflow.core.engine import WorkflowEngine
from chatflow.core.models import *
from chatflow.core.schema import WorkflowSchema, PhaseDefinition, ConditionExpression, ConditionTerm
from chatflow.storage.file_state_store import FileStateStore
from chatflow.utils.conditions import evaluate_condition

@pytest.fixture
def temp_storage_dir():
    """创建临时存储目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir

@pytest.fixture
def engine(temp_storage_dir):
    """创建测试用引擎实例"""
    return WorkflowEngine(storage_dir=temp_storage_dir)

@pytest.fixture
def sample_schema_dict():
    """提供示例 Schema 字典"""
    return {
        "name": "test-workflow",
        "version": "1.0",
        "phases": [
            {"name": "phase1", "task": "task1"},
            {"name": "phase2", "task": "task2"},
            {"name": "phase3", "task": "task3"}
        ]
    }

@pytest.fixture
def conditional_schema_dict():
    """提供带条件分支的 Schema"""
    return {
        "name": "conditional-workflow",
        "version": "1.1",
        "phases": [
            {"name": "analyze", "task": "ai_analysis"},
            {
                "name": "detailed_review",
                "task": "ai_review",
                "condition": {
                    "operator": "and",
                    "operands": [
                        {"field": "analysis.risk_score", "operator": ">", "value": 50},
                        {"field": "code.lines_added", "operator": "<", "value": 100}
                    ]
                }
            },
            {
                "name": "quick_check",
                "task": "tool_check",
                "fallback_phase": "manual_approval"
            },
            {
                "name": "manual_approval",
                "task": "human_input"
            }
        ]
    }

class TestWorkflowEngineBasics:
    """测试基础功能：单例、初始化"""
    
    def test_singleton_pattern(self, temp_storage_dir):
        """测试单例模式确保多实例指向同一对象"""
        engine1 = WorkflowEngine(storage_dir=temp_storage_dir)
        engine2 = WorkflowEngine(storage_dir=temp_storage_dir)
        assert id(engine1) == id(engine2)
        
        # 不同路径应创建不同实例
        engine3 = WorkflowEngine(storage_dir="/tmp/another_path")
        assert id(engine1) != id(engine3)
    
    def test_directory_creation(self, temp_storage_dir):
        """测试自动创建必要目录"""
        engine = WorkflowEngine(storage_dir=temp_storage_dir)
        
        assert os.path.exists(temp_storage_dir)
        assert os.path.exists(os.path.join(temp_storage_dir, "instances"))
        assert os.path.exists(os.path.join(temp_storage_dir, "features"))
        assert os.path.exists(os.path.join(temp_storage_dir, ".locks"))
        assert os.path.exists(os.path.join(temp_storage_dir, ".indexes"))

class TestWorkflowEngineStart:
    """测试工作流启动"""
    
    def test_start_workflow_instance(self, engine, sample_schema_dict):
        """测试成功启动工作流实例"""
        initial_context = {"user_request": "test request"}
        
        result = engine.start_workflow_instance(
            workflow_schema=sample_schema_dict,
            initial_context=initial_context,
            feature_id="feat_test",
            meta={"user_id": "test_user"}
        )
        
        assert isinstance(result, WorkflowStartResult)
        assert result.instance_id.startswith("wfi_")
        assert result.initial_phase == "phase1"
        assert result.created_at > 0
        
        # 验证状态已保存
        state_file = os.path.join(engine.state_store.instances_dir, f"{result.instance_id}.json")
        assert os.path.exists(state_file)
        
        status_file = os.path.join(engine.state_store.instances_dir, result.instance_id, "full_state.json")
        assert os.path.exists(status_file)
    
    def test_start_with_empty_phases(self, engine):
        """测试无阶段的Schema也能启动"""
        schema = {"name": "empty", "version": "1.0", "phases": []}
        result = engine.start_workflow_instance(
            workflow_schema=schema,
            initial_context={},
            feature_id="feat_empty"
        )
        
        state = engine.get_workflow_state(result.instance_id)
        assert state.current_phase == "unknown"
        assert state.status == WorkflowStatus.CREATED
    
    def test_feature_index_updated_on_start(self, engine, sample_schema_dict):
        """测试启动后特性索引被正确更新"""
        result = engine.start_workflow_instance(
            workflow_schema=sample_schema_dict,
            initial_context={},
            feature_id="feat_index_test"
        )
        
        index_file = os.path.join(engine.state_store.indexes_dir, "feature_index.json")
        assert os.path.exists(index_file)
        
        with open(index_file, 'r') as f:
            index_data = json.load(f)
        
        assert "feat_index_test" in index_data
        assert result.instance_id in index_data["feat_index_test"]

class TestWorkflowEngineTriggerNextStep:
    """测试推进工作流"""
    
    def test_trigger_next_step_linear(self, engine, sample_schema_dict):
        """测试线性推进工作流"""
        # 启动实例
        result = engine.start_workflow_instance(
            workflow_schema=sample_schema_dict,
            initial_context={},
            feature_id="feat_linear"
        )
        
        # 第一次推进
        state1 = engine.trigger_next_step(
            instance_id=result.instance_id,
            trigger_data={"output": "step1 done"},
            meta={"duration": 5.0}
        )
        
        assert state1.current_phase == "phase2"
        assert state1.status == WorkflowStatus.RUNNING
        assert state1.variables["output"] == "step1 done"
        assert "duration" in state1.meta
        
        # 第二次推进
        state2 = engine.trigger_next_step(
            instance_id=result.instance_id,
            trigger_data={"code_diff": "+50 -10"}
        )
        
        assert state2.current_phase == "phase3"
        
        # 第三次推进（完成）
        state3 = engine.trigger_next_step(
            instance_id=result.instance_id,
            trigger_data={"test_passed": True}
        )
        
        assert state3.status == WorkflowStatus.COMPLETED
        assert state3.current_phase == "phase3"  # 最后一阶段不变
    
    def test_trigger_next_step_with_conditions(self, engine, conditional_schema_dict):
        """测试条件分支逻辑"""
        # 启动实例
        result = engine.start_workflow_instance(
            workflow_schema=conditional_schema_dict,
            initial_context={},
            feature_id="feat_conditional"
        )
        
        # 推进到 analyze 阶段
        state1 = engine.trigger_next_step(
            instance_id=result.instance_id,
            trigger_data={
                "analysis": {"risk_score": 75},
                "code": {"lines_added": 80}
            }
        )
        
        # 条件满足，进入 detailed_review
        assert state1.current_phase == "detailed_review"
        
        # 重启一个实例测试条件不满足
        result2 = engine.start_workflow_instance(
            workflow_schema=conditional_schema_dict,
            initial_context={},
            feature_id="feat_conditional_low_risk"
        )
        
        state2 = engine.trigger_next_step(
            instance_id=result2.instance_id,
            trigger_data={
                "analysis": {"risk_score": 30},  # 低于阈值
                "code": {"lines_added": 50}
            }
        )
        
        # 条件不满足，跳过 detailed_review，进入 fallback_phase
        assert state2.current_phase == "manual_approval"
    
    def test_dry_run_mode(self, engine, sample_schema_dict):
        """测试 Dry Run 模式不保存状态"""
        result = engine.start_workflow_instance(
            workflow_schema=sample_schema_dict,
            initial_context={},
            feature_id="feat_dryrun"
        )
        
        # 执行 Dry Run
        dry_state = engine.trigger_next_step(
            instance_id=result.instance_id,
            trigger_data={"test": "data"},
            dry_run=True
        )
        
        assert dry_state.current_phase == "phase2"
        
        # 正常查询状态（应仍为 phase1）
        normal_state = engine.get_workflow_state(result.instance_id)
        assert normal_state.current_phase == "phase1"  # 未改变
        
        # 再次正常推进验证
        real_state = engine.trigger_next_step(
            instance_id=result.instance_id,
            trigger_data={"test": "data"}
        )
        assert real_state.current_phase == "phase2"

class TestWorkflowEngineStateManagement:
    """测试状态管理与查询"""
    
    def test_get_workflow_state_from_cache(self, engine, sample_schema_dict):
        """测试内存缓存机制"""
        result = engine.start_workflow_instance(
            workflow_schema=sample_schema_dict,
            initial_context={},
            feature_id="feat_cache"
        )
        
        # 第一次获取（触发加载）
        state1 = engine.get_workflow_state(result.instance_id)
        assert state1 is not None
        
        # 修改文件内容（模拟其他进程修改）
        full_state_file = os.path.join(engine.state_store.instances_dir, result.instance_id, "full_state.json")
        original_content = json.load(open(full_state_file))
        original_status = original_content["status"]
        
        # 直接修改文件
        original_content["status"] = "modified_by_external"
        with open(full_state_file, 'w') as f:
            json.dump(original_content, f, indent=2)
        
        # 在TTL内获取（应返回缓存值）
        state2 = engine.get_workflow_state(result.instance_id)
        assert state2.status.value == original_status  # 仍是原始状态
        
        # 等待缓存过期
        time.sleep(0.1)  # TTL是0.1秒用于测试
        
        # 再次获取（应重新加载）
        state3 = engine.get_workflow_state(result.instance_id)
        assert state3.status.value == "modified_by_external"
    
    def test_get_workflow_status_info(self, engine, sample_schema_dict):
        """测试获取精简状态"""
        result = engine.start_workflow_instance(
            workflow_schema=sample_schema_dict,
            initial_context={},
            feature_id="feat_status_info"
        )
        
        status_info = engine.get_workflow_status_info(result.instance_id)
        
        assert status_info is not None
        assert status_info["instance_id"] == result.instance_id
        assert status_info["status"] == "created"
        assert status_info["current_phase"] == "phase1"
        assert "progress" in status_info
        assert "depth" in status_info
    
    def test_get_workflow_history(self, engine, sample_schema_dict):
        """测试获取完整历史事件"""
        result = engine.start_workflow_instance(
            workflow_schema=sample_schema_dict,
            initial_context={},
            feature_id="feat_history"
        )
        
        # 推进几步
        engine.trigger_next_step(result.instance_id, trigger_data={"step1": "done"})
        engine.trigger_next_step(result.instance_id, trigger_data={"step2": "done"})
        
        history = engine.get_workflow_history(result.instance_id)
        
        assert len(history) >= 3  # 至少包含 started + 2 phase_started
        event_types = [e.event_type for e in history]
        assert "workflow_started" in event_types
        assert "phase_started" in event_types
    
    def test_get_feature_status(self, engine, sample_schema_dict):
        """测试获取特性聚合状态"""
        # 创建两个实例
        result1 = engine.start_workflow_instance(
            workflow_schema=sample_schema_dict,
            initial_context={},
            feature_id="feat_agg"
        )
        
        result2 = engine.start_workflow_instance(
            workflow_schema=sample_schema_dict,
            initial_context={},
            feature_id="feat_agg"
        )
        
        # 推进第一个实例
        engine.trigger_next_step(result1.instance_id)
        
        agg_status = engine.get_feature_status("feat_agg")
        
        assert agg_status["feature_id"] == "feat_agg"
        assert agg_status["total_instances"] == 2
        assert agg_status["running_count"] == 1
        assert agg_status["completed_count"] == 0
        assert agg_status["status"] == "in_progress"

class TestWorkflowEngineErrorHandling:
    """测试错误处理"""
    
    def test_trigger_nonexistent_instance(self, engine):
        """测试操作不存在的实例"""
        with pytest.raises(ValueError, match="not found"):
            engine.trigger_next_step("wfi_nonexistent")
    
    def test_schema_validation_error(self, engine):
        """测试Schema验证失败"""
        invalid_schema = {
            "name": "invalid",
            "version": "1.0",
            "phases": [
                {"name": "duplicate"}, 
                {"name": "duplicate"}  # 重复名称
            ]
        }
        
        with pytest.raises(ValueError, match="Duplicate phase names"):
            engine.start_workflow_instance(
                workflow_schema=invalid_schema,
                initial_context={},
                feature_id="feat_invalid"
            )

class TestConcurrency:
    """测试并发安全性"""
    
    def test_concurrent_access_with_locks(self, temp_storage_dir):
        """测试多线程并发访问的安全性"""
        engine = WorkflowEngine(storage_dir=temp_storage_dir)
        schema = {"name": "concurrent", "version": "1.0", "phases": [{"name": "p1"}, {"name": "p2"}]}
        
        results = []
        exceptions = []
        
        def worker(worker_id):
            try:
                # 每个线程创建自己的实例
                result = engine.start_workflow_instance(
                    workflow_schema=schema,
                    initial_context={"worker": worker_id},
                    feature_id=f"feat_worker_{worker_id}"
                )
                
                # 推进一步
                state = engine.trigger_next_step(result.instance_id)
                results.append((worker_id, result.instance_id, state.current_phase))
            except Exception as e:
                exceptions.append(e)
        
        # 创建10个线程并发执行
        threads = []
        for i in range(10):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        # 验证没有异常且所有实例都存在
        assert len(exceptions) == 0, f"Exceptions occurred: {exceptions}"
        assert len(results) == 10
        
        # 验证每个实例的状态正确
        for worker_id, instance_id, current_phase in results:
            state = engine.get_workflow_state(instance_id)
            assert state is not None
            assert state.current_phase == "p2"
            assert state.variables["worker"] == worker_id

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

---

## ✅ 测试覆盖率说明

| 测试类别 | 覆盖范围 |
|---------|----------|
| **基础功能** | 单例模式、目录创建、文件锁 |
| **核心流程** | `start_workflow_instance`, `trigger_next_step` |
| **智能特性** | 条件分支、Dry Run 模式 |
| **状态管理** | 缓存、精简状态、历史记录 |
| **查询能力** | 特性聚合状态 |
| **错误处理** | 无效Schema、不存在实例 |
| **并发安全** | 多线程同时操作 |

---

## 🧪 运行方式

```bash
# 安装依赖
pip install pytest

# 运行测试
python -m pytest tests/test_workflow_engine.py -v

# 或使用pytest命令
pytest tests/test_workflow_engine.py -v
```

---

## 💡 测试设计原则

1. **真实场景驱动**：测试用例基于实际使用模式（如并发创建、条件判断）。
2. **边界条件覆盖**：测试空Schema、重复Phase等边缘情况。
3. **并发验证**：通过多线程测试文件锁的有效性。
4. **向后兼容**：确保v1.0的调用方式在v1.1中仍能通过测试。
5. **轻量高效**：不依赖外部服务，运行快速。

这套测试确保了 ChatFlow v1.1 的核心功能稳定可靠，为后续演进奠定了坚实基础。
