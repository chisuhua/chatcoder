# chatcoder/core/engine.py
"""
ChatCoder 核心服务 - 工作流引擎 (WorkflowEngine) [适配器]
负责加载工作流定义、管理特性状态和进行智能阶段推荐。
[注意] 此类现在是 chatflow 库的适配器。
"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
# --- 导入 ChatCoder 内部依赖 ---
from .orchestrator import TaskOrchestrator
from .models import TaskStatus

# --- 导入 chatflow 库 (如果可用) ---
try:
    # 从 chatflow 库导入核心类
    from chatflow.core.workflow_engine import WorkflowEngine as ChatFlowEngine
    from chatflow.core.state import IWorkflowStateStore
    from chatflow.core.file_state_store import FileWorkflowStateStore
    from chatflow.core.models import WorkflowInstanceState, WorkflowInstanceStatus
    CHATFLOW_AVAILABLE = True
    print("✅ chatflow library successfully imported.")
except ImportError:
    # 如果 chatflow 库不可用（例如，尚未安装或在旧版本中），则回退到旧逻辑
    print("⚠️  Warning: chatflow library not found. Using legacy WorkflowEngine implementation.")
    CHATFLOW_AVAILABLE = False
    ChatFlowEngine = None
    IWorkflowStateStore = object # 一个无操作的基类作为占位符
    FileWorkflowStateStore = None
    WorkflowInstanceState = Dict # 占位符
    WorkflowInstanceStatus = object # 占位符


# 项目根目录和模板目录 (与 workflow.py 保持一致)
PROJECT_ROOT = Path(__file__).parent.parent.parent
TEMPLATES_DIR = PROJECT_ROOT / "ai-prompts"


def get_workflow_path() -> Path:
    """获取工作流定义文件的目录路径"""
    return TEMPLATES_DIR / "workflows"


class WorkflowEngine:
    """
    工作流引擎 (适配器)，用于管理 ChatCoder 的工作流和特性状态。
    [注意] 此类现在是 chatflow 库的适配器。
    """

    def __init__(self, task_orchestrator: Optional[TaskOrchestrator] = None):
        """
        初始化工作流引擎 (适配器)。

        Args:
            task_orchestrator (Optional[TaskOrchestrator]):
                用于访问任务状态的 TaskOrchestrator 实例。
        """
        if task_orchestrator is None:
            self.task_orchestrator = TaskOrchestrator()
        else:
            self.task_orchestrator = task_orchestrator

        self._chatflow_engine: Optional[ChatFlowEngine] = None
        if CHATFLOW_AVAILABLE:
            try:
                state_store = FileWorkflowStateStore()
                self._chatflow_engine = ChatFlowEngine(state_store=state_store_adapter)
                print("✅ chatflow engine successfully initialized as adapter.")
            except Exception as e:
                print(f"⚠️  Warning: Failed to initialize chatflow engine: {e}")
                self._chatflow_engine = None


    def get_workflow_path(self) -> Path:
        """
        获取工作流定义文件的目录路径。
        (实例方法版本，供内部使用)

        Returns:
            Path: 工作流目录的 Path 对象。
        """
        return get_workflow_path()

    # --- 修改：委派给 chatflow 或使用旧逻辑 ---
    def load_workflow_schema(self, name: str = "default") -> dict:
        """
        加载指定名称的工作流模式（YAML 定义）。
        """
        if self._chatflow_engine:
            try:
                return self._chatflow_engine.load_workflow_schema(name)
            except Exception as e:
                print(f"⚠️  Delegating to legacy load_workflow_schema due to error: {e}")
                # Fallback to legacy if chatflow fails
                pass

        # --- 旧逻辑 (作为后备或 chatflow 不可用时) ---
        custom_path = self.get_workflow_path() / f"{name}.yaml"
        if custom_path.exists():
            return yaml.safe_load(custom_path.read_text(encoding="utf-8"))
        raise ValueError(f"Workflows schema not found: {name}")

    def get_phase_order(self, schema: dict) -> Dict[str, int]:
        """
        从工作流 schema 中提取阶段名称到其顺序的映射。
        """
        if self._chatflow_engine:
             # ChatFlow 的方法可以直接使用
             try:
                 return self._chatflow_engine.get_phase_order(schema)
             except Exception as e:
                 print(f"⚠️  Delegating to legacy get_phase_order due to error: {e}")
                 # Fallback to legacy if chatflow fails
                 pass

        # --- 旧逻辑 (后备) ---
        return {phase["name"]: idx for idx, phase in enumerate(schema["phases"])}

    def get_next_phase(self, schema: dict, current_phase: str) -> Optional[str]:
        """
        根据工作流 schema 获取下一个阶段的名称。
        """
        if self._chatflow_engine:
            try:
                return self._chatflow_engine.get_next_phase(schema, current_phase)
            except Exception as e:
                print(f"⚠️  Delegating to legacy get_next_phase due to error: {e}")
                # Fallback to legacy if chatflow fails
                pass

        # --- 旧逻辑 (后备) ---
        order = self.get_phase_order(schema)
        if current_phase not in order:
            return schema["phases"][0]["name"] if schema["phases"] else None
        current_idx = order[current_phase]
        if current_idx + 1 < len(schema["phases"]):
            return schema["phases"][current_idx + 1]["name"]
        return None

    def get_feature_status(self, feature_id: str, schema_name: str = "default") -> Dict[str, Any]:
        """
        获取指定特性的完整状态，包括当前阶段、下一阶段、完成度等。
        """
        if self._chatflow_engine:
            try:
                # 注意：这里可能会调用到 ChatFlow Engine 中依赖 state_store 查询的方法
                return self._chatflow_engine.get_feature_status(feature_id, schema_name)
            except NotImplementedError as nie:
                 print(f"⚠️  ChatFlow get_feature_status not fully implemented ({nie}), falling back to legacy.")
            except Exception as e:
                 print(f"⚠️  Delegating to legacy get_feature_status due to error: {e}")
                 # Fallback to legacy if chatflow fails unexpectedly
                 pass

        # --- 旧逻辑 (后备或 chatflow 不可用/不完整时) ---
        tasks = self.task_orchestrator.list_task_states()
        try:
            schema = self.load_workflow_schema(schema_name)
        except ValueError as e:
            raise e
        phase_order = self.get_phase_order(schema)

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

        for phase in schema["phases"]:
            status["phases"][phase["name"]] = "not-started"

        for task in tasks:
            if task.get("feature_id") == feature_id:
                phase_name = task["phase"]
                if phase_name in status["phases"]:
                    task_status = task["status"]
                    # 简单映射示例 (可根据实际需求调整)
                    mapped_status = "completed" if task_status == TaskStatus.CONFIRMED.value else task_status
                    status["phases"][phase_name] = mapped_status

        ordered_phases = sorted(
            [p for p in schema["phases"] if p["name"] in status["phases"]],
            key=lambda x: phase_order[x["name"]]
        )

        completed_phases = [
            p["name"] for p in ordered_phases
            if status["phases"][p["name"]] == "completed"
        ]

        if completed_phases:
            last_completed = completed_phases[-1]
            status["current_phase"] = last_completed
            status["next_phase"] = self.get_next_phase(schema, last_completed)
        else:
            first_phase = ordered_phases[0]["name"] if ordered_phases else None
            status["current_phase"] = None
            status["next_phase"] = first_phase

        status["completed_count"] = len(completed_phases)
        return status

    def determine_next_phase(self, current_phase: str, ai_response_content: str, context: Dict[str, Any]) -> Optional[str]:
        """
        基于AI响应内容和上下文智能决策下一阶段。
        """
        if self._chatflow_engine:
            try:
                return self._chatflow_engine.determine_next_phase(current_phase, ai_response_content, context)
            except Exception as e:
                print(f"⚠️  Delegating to legacy determine_next_phase due to error: {e}")
                # Fallback to legacy if chatflow fails
                pass

        # --- 旧逻辑 (后备) ---
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
        为给定特性推荐下一个阶段，考虑智能决策。
        """
        if self._chatflow_engine:
            try:
                return self._chatflow_engine.recommend_next_phase(feature_id, schema_name)
            except NotImplementedError as nie:
                 print(f"⚠️  ChatFlow recommend_next_phase not fully implemented ({nie}), falling back to legacy.")
            except Exception as e:
                 print(f"⚠️  Delegating to legacy recommend_next_phase due to error: {e}")
                 # Fallback to legacy if chatflow fails unexpectedly
                 pass

        # --- 旧逻辑 (后备) ---
        status = self.get_feature_status(feature_id, schema_name)
        if not status.get("next_phase"):
            return None

        standard_next_phase = status.get("next_phase")
        current_phase = status.get("current_phase")

        # 使用 TaskOrchestrator 获取任务列表
        all_tasks = self.task_orchestrator.list_task_states()
        confirmed_tasks = [
            t for t in all_tasks
            if t["feature_id"] == feature_id and t["status"] == TaskStatus.CONFIRMED.value
        ]

        if not confirmed_tasks:
            return {
                "phase": standard_next_phase,
                "reason": "No confirmed tasks found for feature, following standard workflow.",
                "source": "standard",
                "current_phase": current_phase
            }

        # 假设列表是按时间倒序排列的
        last_confirmed_task_summary = confirmed_tasks[0]
        last_confirmed_task_id = last_confirmed_task_summary["task_id"]

        # 使用 TaskOrchestrator 加载任务详情
        last_task_data = self.task_orchestrator.load_task_state(last_confirmed_task_id)
        if not last_task_data:
            return {
                "phase": standard_next_phase,
                "reason": f"Could not load details for last confirmed task {last_confirmed_task_id}, following standard workflow.",
                "source": "standard fallback",
                "current_phase": current_phase
            }

        ai_response_content = last_task_data.get("context", {}).get("rendered", "")
        task_context = last_task_data.get("context", {})

        smart_next_phase = self.determine_next_phase(
            current_phase or last_task_data.get("phase", ""),
            ai_response_content,
            task_context
        )

        if smart_next_phase and smart_next_phase != standard_next_phase:
            return {
                "phase": smart_next_phase,
                "reason": f"Smart recommendation based on analysis of task {last_confirmed_task_id}'s output.",
                "source": "smart",
                "current_phase": current_phase
            }
        else:
            return {
                "phase": standard_next_phase,
                "reason": "Following standard workflow sequence.",
                "source": "standard",
                "current_phase": current_phase
            }
    # --- 修改结束 ---
