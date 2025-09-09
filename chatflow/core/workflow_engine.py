# chatflow/core/workflow_engine.py
"""
ChatFlow 核心实现 - 工作流引擎 (WorkflowEngine)
提供工作流定义加载、特性状态管理和智能阶段推荐的具体实现。
并管理 WorkflowInstanceState 的生命周期。
"""

import yaml
import uuid
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import asdict # 需要导入 asdict 来处理 dataclass 对象
from .engine import IWorkflowEngine
from .state import IWorkflowStateStore
from .models import WorkflowInstanceState, WorkflowInstanceStatus, WorkflowDefinition

# --- 配置 ---
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
TEMPLATES_DIR = PROJECT_ROOT / "ai-prompts"

def get_workflow_path() -> Path:
    """获取工作流定义文件的目录路径 (内部辅助函数)"""
    return TEMPLATES_DIR / "workflows"

class WorkflowEngine(IWorkflowEngine):
    """
    工作流引擎的具体实现，管理 WorkflowInstanceState 生命周期。
    """

    def __init__(self, state_store: IWorkflowStateStore):
        """
        初始化工作流引擎。
        """
        self.state_store = state_store

    def get_workflow_path(self) -> Path:
        """获取工作流定义文件的目录路径。"""
        return get_workflow_path()

    def load_workflow_schema(self, name: str = "default") -> dict:
        """加载指定名称的工作流模式（YAML 定义）。"""
        custom_path = self.get_workflow_path() / f"{name}.yaml"
        if custom_path.exists():
            return yaml.safe_load(custom_path.read_text(encoding="utf-8"))
        raise ValueError(f"Workflows schema not found: {name}")

    def get_phase_order(self, schema) -> Dict[str, int]:
        """
        从工作流 schema 中提取阶段名称到其顺序的映射。

        Args:
            schema (Union[dict, WorkflowDefinition]): 工作流 schema 字典或 WorkflowDefinition 对象。

        Returns:
            Dict[str, int]: 阶段名称到顺序索引的映射。
        """
        # --- 修改点：增强兼容性，处理 dict 或 WorkflowDefinition 对象 ---
        if hasattr(schema, 'phases'): # 检查是否为 WorkflowDefinition 对象
            # 如果是对象，则访问其 .phases 属性
            phases = schema.phases
        elif isinstance(schema, dict) and 'phases' in schema:
            # 如果是字典，则访问其 ['phases'] 键
            phases = schema['phases']
        else:
            # 如果都不是，抛出错误或返回空字典 (更健壮的做法是抛出错误)
            raise TypeError(f"Invalid schema type or missing 'phases' key: {type(schema)}, value: {schema}")
        # --- 修改点结束 ---
        
        # 统一处理 phases 列表
        # phases 列表中的元素现在可能是 dict (来自 YAML) 或 WorkflowPhaseDefinition 对象
        return {
            # --- 修改点：增强兼容性，处理 phases 列表中的元素 ---
            # phase["name"]: idx for idx, phase in enumerate(phases) # 旧的，仅处理 dict
            (phase.name if hasattr(phase, 'name') else phase["name"]): idx # 新的，处理对象或字典
            for idx, phase in enumerate(phases)
            # --- 修改点结束 ---
        }

    def get_next_phase(self, schema, current_phase: str) -> Optional[str]:
        """
        根据工作流 schema 获取下一个阶段的名称。

        Args:
            schema (Union[dict, WorkflowDefinition]): 工作流 schema 字典或 WorkflowDefinition 对象。
            current_phase (str): 当前阶段名称。

        Returns:
            Optional[str]: 下一个阶段名称，如果已是最后一个阶段则返回 None。
        """
        # --- 修改点：使用改进后的 get_phase_order ---
        try:
            order = self.get_phase_order(schema) # 这个方法现在可以处理对象或字典了
        except TypeError as e:
            print(f"⚠️  [get_next_phase] Error in get_phase_order: {e}")
            return None # 或抛出异常
        # --- 修改点结束 ---
        
        if current_phase not in order:
            # --- 修改点：增强兼容性，处理 schema 对象或字典以获取第一个阶段 ---
            # return schema["phases"][0]["name"] if schema["phases"] else None # 旧的
            try:
                if hasattr(schema, 'phases') and schema.phases: # 新的，处理对象
                    first_phase = schema.phases[0]
                    return first_phase.name if hasattr(first_phase, 'name') else first_phase["name"]
                elif isinstance(schema, dict) and schema.get("phases"): # 新的，处理字典
                    return schema["phases"][0]["name"]
                else:
                    return None # 如果 schema 为空或无效
            except (IndexError, KeyError, AttributeError) as e:
                print(f"⚠️  [get_next_phase] Error getting first phase: {e}")
                return None
            # --- 修改点结束 ---

        current_idx = order[current_phase]
        # --- 修改点：增强兼容性，处理 schema 对象或字典以获取阶段列表 ---
        # if current_idx + 1 < len(schema["phases"]): # 旧的
        try:
            phases_list = schema.phases if hasattr(schema, 'phases') else schema.get("phases", []) # 新的
        except AttributeError:
            print(f"⚠️  [get_next_phase] Schema object missing 'phases' attribute.")
            return None
        # --- 修改点结束 ---
        if current_idx + 1 < len(phases_list):
            # --- 修改点：增强兼容性，处理阶段对象或字典以获取名称 ---
            # return schema["phases"][current_idx + 1]["name"] # 旧的
            try:
                next_phase = phases_list[current_idx + 1] # 新的
                return next_phase.name if hasattr(next_phase, 'name') else next_phase["name"]
            except (IndexError, KeyError, AttributeError) as e:
                print(f"⚠️  [get_next_phase] Error getting next phase name: {e}")
                return None
            # --- 修改点结束 ---
        
        return None  # 已到最后

    def start_workflow_instance(self, workflow_definition: WorkflowDefinition, initial_context: Dict[str, Any], feature_id: str) -> str:
        """
        启动一个新的工作流实例。
        """
        instance_id = f"wfi_{uuid.uuid4().hex[:12]}"
        now_iso = datetime.now().isoformat()
        
        # 确定起始阶段 (通常是第一个阶段)
        starting_phase = workflow_definition.phases[0].name if workflow_definition.phases else None

        initial_state = WorkflowInstanceState(
            instance_id=instance_id,
            feature_id=feature_id,
            workflow_name=workflow_definition.name,
            current_phase=starting_phase,
            history=[],
            variables=initial_context, # 将初始上下文存为变量
            status=WorkflowInstanceStatus.CREATED,
            created_at=now_iso,
            updated_at=now_iso
        )
        
        # 保存初始状态
        self.save_workflow_instance_state(initial_state)
        print(f"✅ Started new workflow instance: {instance_id} for feature: {feature_id}")
        return instance_id

    def trigger_next_step(self, instance_id: str, trigger_data: Optional[Dict[str, Any]] = None) -> WorkflowInstanceState:
        """
        触发工作流实例的下一步执行。
        这是一个简化的示例实现，实际逻辑会更复杂。
        """
        # 1. 加载当前实例状态
        current_state = self.load_workflow_instance_state(instance_id)
        if not current_state:
            raise ValueError(f"Workflow instance {instance_id} not found.")

        # 2. 简单示例逻辑：更新状态并前进到下一阶段
        #    实际中，这里会分析 trigger_data, 执行任务，更新 variables/history
        current_state.history.append({
            "phase": current_state.current_phase,
            "triggered_at": datetime.now().isoformat(),
            "trigger_data_summary": str(trigger_data)[:100] + "..." if trigger_data and len(str(trigger_data)) > 100 else str(trigger_data)
        })

        # 3. 获取工作流定义以确定下一阶段
        try:
            workflow_schema = self.load_workflow_schema(current_state.workflow_name)
            next_phase = self.get_next_phase(workflow_schema, current_state.current_phase or "")
            if next_phase:
                current_state.current_phase = next_phase
                current_state.status = WorkflowInstanceStatus.RUNNING
            else:
                # 如果没有下一阶段，标记为完成
                current_state.status = WorkflowInstanceStatus.COMPLETED
        except ValueError as e:
            print(f"⚠️  Error loading workflow schema for {instance_id}: {e}")
            current_state.status = WorkflowInstanceStatus.FAILED

        # 4. 更新时间戳
        current_state.updated_at = datetime.now().isoformat()

        # 5. 保存更新后的状态
        self.save_workflow_instance_state(current_state)

        print(f"✅ Triggered next step for instance {instance_id}. New phase: {current_state.current_phase}, Status: {current_state.status.value}")
        return current_state

    def save_workflow_instance_state(self, state: WorkflowInstanceState) -> None:
        """
        保存工作流实例状态到状态存储。
        (内部辅助方法)
        """
        # 更新最后更新时间
        state.updated_at = datetime.now().isoformat()
        # 转换为字典并保存
        state_dict = {
            "instance_id": state.instance_id,
            "feature_id": state.feature_id,
            "workflow_name": state.workflow_name,
            "current_phase": state.current_phase,
            "history": state.history,
            "variables": state.variables,
            "status": state.status.value, # 存储枚举的字符串值
            "created_at": state.created_at,
            "updated_at": state.updated_at,
        }
        self.state_store.save_state(state.instance_id, state_dict)

    def load_workflow_instance_state(self, instance_id: str) -> Optional[WorkflowInstanceState]:
        """
        从状态存储加载工作流实例状态。
        (内部辅助方法)
        """
        state_dict = self.state_store.load_state(instance_id)
        if not state_dict:
            return None
            
        # 转换回 WorkflowInstanceState 对象
        try:
            status_str = state_dict.pop("status", "created")
            status_enum = WorkflowInstanceStatus(status_str)
            state_dict["status"] = status_enum
            
            # Handle history and variables if they are not in the dict
            state_dict.setdefault("history", [])
            state_dict.setdefault("variables", {})
            
            return WorkflowInstanceState(**state_dict)
        except (KeyError, TypeError, ValueError) as e:
            # Log error or handle corrupted state
            print(f"Error loading workflow instance state for {instance_id}: {e}")
            return None

    def get_workflow_instance_status(self, instance_id: str) -> Optional[WorkflowInstanceState]:
        """
        获取指定工作流实例的当前状态。

        Args:
            instance_id (str): 工作流实例 ID。

        Returns:
            Optional[WorkflowInstanceState]: 工作流实例状态对象。
        """
        return self.load_workflow_instance_state(instance_id)

    # --- 修改：更新原有方法以使用实例状态 ---

    def get_feature_status(self, feature_id: str, schema_name: str = "default") -> Dict[str, Any]:
        """
        获取指定特性的完整状态，通过查询关联的工作流实例。
        """
        try:
            schema = self.load_workflow_schema(schema_name)
        except ValueError as e:
            raise e


        try:
            # 假设 IWorkflowStateStore 已扩展 list_instances_by_feature
            instance_states_data = self.state_store.list_instances_by_feature(feature_id)
        except (AttributeError, NotImplementedError):
            print("Warning: State store does not fully support list_instances_by_feature. Feature status might be incomplete.")
            instance_states_data = []

        status = {
            "feature_id": feature_id,
            "schema": schema.get("name", schema_name),
            "workflow": schema_name,
            "phases": {},
            "current_phase": None,
            "next_phase": None,
            "completed_count": 0,
            "total_count": len(schema["phases"])
        }

        # 初始化所有 phase 状态 (基于 schema)
        for phase in schema["phases"]:
            status["phases"][phase["name"]] = "not-started"

        # 基于实例状态聚合特性状态
        completed_phases = set()
        all_phases_encountered = set()

        for state_data in instance_states_data:
            phase_name = state_data.get("current_phase")
            if phase_name:
                all_phases_encountered.add(phase_name)
                # 简单示例：如果实例状态是 COMPLETED，则认为阶段完成
                # 实际逻辑可能更复杂
                status_from_instance = state_data.get("status")
                if status_from_instance == WorkflowInstanceStatus.COMPLETED.value:
                    status["phases"][phase_name] = "completed"
                    completed_phases.add(phase_name)
                elif status_from_instance in [WorkflowInstanceStatus.RUNNING.value, WorkflowInstanceStatus.PAUSED.value]:
                     status["phases"][phase_name] = "in-progress"
                else: # CREATED, FAILED
                     status["phases"][phase_name] = "started"

        # 确定当前和下一个阶段 (简化版逻辑)
        phase_order = self.get_phase_order(schema)
        ordered_phases = sorted(schema["phases"], key=lambda p: phase_order[p["name"]])

        last_completed_phase = None
        for phase_info in reversed(ordered_phases):
            if phase_info["name"] in completed_phases:
                last_completed_phase = phase_info["name"]
                break

        status["current_phase"] = last_completed_phase
        if last_completed_phase:
            status["next_phase"] = self.get_next_phase(schema, last_completed_phase)
        elif ordered_phases:
            status["next_phase"] = ordered_phases[0]["name"]

        status["completed_count"] = len(completed_phases)
        return status

    def determine_next_phase(self, current_phase: str, ai_response_content: str, context: Dict[str, Any]) -> Optional[str]:
        """
        基于AI响应内容和上下文智能决策下一阶段。
        """
        content_lower = ai_response_content.lower()
        if "security" in content_lower and ("risk" in content_lower or "impact" in content_lower):
            return "security_review"
        if "new library" in content_lower or "significant architectural change" in content_lower:
            return "tech_spike"
        if "database migration" in content_lower:
            return "migration_plan"
        return None

    def recommend_next_phase(self, feature_id: str, schema_name: str = "default") -> Optional[Dict[str, Any]]:
        """
        为给定特性推荐下一个阶段。
        """
        status = self.get_feature_status(feature_id, schema_name)

        if not status.get("next_phase"):
            return None

        standard_next_phase = status.get("next_phase")
        current_phase = status.get("current_phase")

        return {
            "phase": standard_next_phase,
            "reason": "Following standard workflow sequence or smart decision based on instance analysis.",
            "source": "standard_or_smart",
            "current_phase": current_phase
        }
