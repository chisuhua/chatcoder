# chatcoder/core/engine.py
"""
ChatCoder 核心服务 - 工作流引擎 (WorkflowEngine)
负责加载工作流定义、管理特性状态和进行智能阶段推荐。
"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
from .orchestrator import TaskOrchestrator
from .models import TaskStatus

PROJECT_ROOT = Path(__file__).parent.parent.parent
TEMPLATES_DIR = PROJECT_ROOT / "ai-prompts"


def get_workflow_path() -> Path:
    """获取工作流定义文件的目录路径"""
    return TEMPLATES_DIR / "workflows"


class WorkflowEngine:
    """
    工作流引擎，负责管理 ChatCoder 的工作流和特性状态。
    """

    def __init__(self, task_orchestrator: Optional[TaskOrchestrator] = None):
        """
        初始化工作流引擎。
        """
        if task_orchestrator is None:
            self.task_orchestrator = TaskOrchestrator()
        else:
            self.task_orchestrator = task_orchestrator

    def get_workflow_path(self) -> Path:
        """
        获取工作流定义文件的目录路径。
        """
        return get_workflow_path()

    def load_workflow_schema(self, name: str = "default") -> dict:
        """
        加载指定名称的工作流模式（YAML 定义）。
        """
        custom_path = self.get_workflow_path() / f"{name}.yaml"
        if custom_path.exists():
            return yaml.safe_load(custom_path.read_text(encoding="utf-8"))

        raise ValueError(f"Workflows schema not found: {name}")

    def get_phase_order(self, schema: dict) -> Dict[str, int]:
        """
        从工作流 schema 中提取阶段名称到其顺序的映射。
        """
        return {phase["name"]: idx for idx, phase in enumerate(schema["phases"])}

    def get_next_phase(self, schema: dict, current_phase: str) -> Optional[str]:
        """
        根据工作流 schema 获取下一个阶段的名称。
        """
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
        status = self.get_feature_status(feature_id, schema_name)

        if not status.get("next_phase"):
            return None

        standard_next_phase = status.get("next_phase")
        current_phase = status.get("current_phase")

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

        last_confirmed_task_summary = confirmed_tasks[0]
        last_confirmed_task_id = last_confirmed_task_summary["task_id"]

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
