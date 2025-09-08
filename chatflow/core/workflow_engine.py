# chatflow/core/workflow_engine.py
"""
ChatFlow 核心实现 - 工作流引擎 (WorkflowEngine)
提供工作流定义加载、特性状态管理和智能阶段推荐的具体实现。
"""

import yaml
import uuid
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from .engine import IWorkflowEngine
from .state import IWorkflowStateStore
from .models import WorkflowInstanceState, WorkflowInstanceStatus # 导入新模型

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

    def get_phase_order(self, schema: dict) -> Dict[str, int]:
        """从工作流 schema 中提取阶段名称到其顺序的映射。"""
        return {phase["name"]: idx for idx, phase in enumerate(schema["phases"])}

    def get_next_phase(self, schema: dict, current_phase: str) -> Optional[str]:
        """根据工作流 schema 获取下一个阶段的名称。"""
        order = self.get_phase_order(schema)
        if current_phase not in order:
            return schema["phases"][0]["name"] if schema["phases"] else None
        current_idx = order[current_phase]
        if current_idx + 1 < len(schema["phases"]):
            return schema["phases"][current_idx + 1]["name"]
        return None

    # --- 新增：工作流实例生命周期管理方法 ---
    
    def start_workflow_instance(self, workflow_definition: dict, initial_context: Dict[str, Any], feature_id: str) -> str:
        """
        启动一个新的工作流实例。

        Args:
            workflow_definition (dict): 工作流定义 schema。
            initial_context (Dict[str, Any]): 初始上下文。
            feature_id (str): 关联的 ChatCoder 特性 ID。

        Returns:
            str: 新创建的工作流实例 ID。
        """
        instance_id = f"wfi_{uuid.uuid4().hex[:12]}"
        now_iso = datetime.now().isoformat()
        
        initial_state = WorkflowInstanceState(
            instance_id=instance_id,
            feature_id=feature_id,
            workflow_name=workflow_definition.get("name", "unknown"),
            current_phase=None, # 初始阶段将在第一次推荐时确定
            history=[],
            variables=initial_context, # 将初始上下文存为变量
            status=WorkflowInstanceStatus.CREATED,
            created_at=now_iso,
            updated_at=now_iso
        )
        
        # 保存初始状态
        self.save_workflow_instance_state(initial_state)
        return instance_id

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
        except AttributeError:
            # 如果 state_store 实现不支持，需要一个 fallback 或抛出错误
            # 这表明 state_store 实现需要更新
            print("Warning: State store does not support list_instances_by_feature. Feature status might be incomplete.")
            instance_states_data = []
        except NotImplementedError:
             print("Warning: State store list_instances_by_feature not implemented. Feature status might be incomplete.")
             instance_states_data = []

        # 将字典数据转换为 WorkflowInstanceState 对象 (如果需要内部处理)
        # instance_states = [self.load_workflow_instance_state(data['instance_id']) for data in instance_states_data if data]
        # 为简化，直接使用字典数据进行聚合

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
        # 简化逻辑：假设每个实例代表一个阶段的执行或尝试
        # 更复杂的逻辑可能需要分析 instance_state.history
        completed_phases = set()
        all_phases_encountered = set()

        for state_data in instance_states_data:
            # state_obj = self.load_workflow_instance_state(state_data.get('instance_id'))
            # if not state_obj: continue
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
                     status["phases"][phase_name] = "started" # 或其他状态

        # 确定当前和下一个阶段 (简化版逻辑)
        phase_order = self.get_phase_order(schema)
        ordered_phases = sorted(schema["phases"], key=lambda p: phase_order[p["name"]])

        last_completed_phase = None
        for phase_info in reversed(ordered_phases): # 从后往前找最后一个完成的
            if phase_info["name"] in completed_phases:
                last_completed_phase = phase_info["name"]
                break

        status["current_phase"] = last_completed_phase
        if last_completed_phase:
            status["next_phase"] = self.get_next_phase(schema, last_completed_phase)
        elif ordered_phases:
            status["next_phase"] = ordered_phases[0]["name"] # 第一个阶段

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
        try:
            status = self.get_feature_status(feature_id, schema_name)
        except NotImplementedError:
            raise 

        if not status.get("next_phase"):
            return None

        standard_next_phase = status.get("next_phase")
        current_phase = status.get("current_phase")

        # --- 简化：这里不再直接查询 ChatCoder 任务 ---
        # 因为 ChatFlow 现在管理自己的实例状态，它应该有足够的信息来做决定
        # 或者，这个方法可以只返回阶段名称，让 ChatCoder 决定如何处理
        
        # 为了兼容旧接口，我们仍然返回字典
        # 但逻辑基于 ChatFlow 内部状态
        
        # (这里可以添加更复杂的逻辑，例如查询特定实例的详细输出进行分析)
        # 为了演示，我们使用一个简化的逻辑
        
        # 假设我们总是有实例数据，可以进行分析
        # 实际上，get_feature_status 内部已经聚合了实例信息
        # 我们可以在这里添加更精细的决策，但现在直接使用标准逻辑
        
        # 一个更真实的例子：分析最后一个实例的输出
        # 但这需要保存 AI 输出到 instance_state.history 或 variables 中
        # instance_states_data = self.state_store.list_instances_by_feature(feature_id)
        # if instance_states_data:
        #     # 分析最后一个实例...
        #     # smart_phase = self.determine_next_phase(...)
        #     # if smart_phase: ...
        #     pass

        return {
            "phase": standard_next_phase,
            "reason": "Following standard workflow sequence or smart decision based on instance analysis.",
            "source": "standard_or_smart", # 或 "chatflow_internal"
            "current_phase": current_phase
        }
    # --- 修改结束 ---
