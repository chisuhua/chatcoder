# chatcoder/core/engine.py
"""
ChatCoder 核心服务 - 工作流引擎 (WorkflowEngine)
负责加载工作流定义、管理特性状态和进行智能阶段推荐。
"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
# from .state import list_task_states # 不再直接使用，改用 TaskOrchestrator
# --- 新增/确认导入 ---
from .orchestrator import TaskOrchestrator # 用于获取任务详情
from .models import TaskStatus # 用于状态检查
# --- 新增/确认导入结束 ---

# 项目根目录和模板目录 (与 workflow.py 保持一致)
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

        Args:
            task_orchestrator (Optional[TaskOrchestrator]):
                用于访问任务状态的 TaskOrchestrator 实例。
                如果未提供，将创建一个新的实例（不推荐用于生产，主要用于向后兼容）。
        """
        if task_orchestrator is None:
            # 为了向后兼容或在某些简单场景下使用，可以创建一个新实例
            # 但在 CLI 中，最好传入已存在的实例以确保一致性
            self.task_orchestrator = TaskOrchestrator()
            # print("Warning: WorkflowEngine created its own TaskOrchestrator instance.")
        else:
            self.task_orchestrator = task_orchestrator

    def get_workflow_path(self) -> Path:
        """
        获取工作流定义文件的目录路径。
        (实例方法版本，供内部使用)

        Returns:
            Path: 工作流目录的 Path 对象。
        """
        return get_workflow_path()

    def load_workflow_schema(self, name: str = "default") -> dict:
        """
        加载指定名称的工作流模式（YAML 定义）。

        Args:
            name (str, optional): 工作流名称 (默认 "default")。

        Returns:
            dict: 解析后的工作流 schema 字典。

        Raises:
            ValueError: 如果指定的工作流文件未找到。
        """
        # 尝试从 workflows 目录加载
        custom_path = self.get_workflow_path() / f"{name}.yaml"
        if custom_path.exists():
            return yaml.safe_load(custom_path.read_text(encoding="utf-8"))

        raise ValueError(f"Workflows schema not found: {name}")

    def get_phase_order(self, schema: dict) -> Dict[str, int]:
        """
        从工作流 schema 中提取阶段名称到其顺序的映射。

        Args:
            schema (dict): 工作流 schema 字典。

        Returns:
            Dict[str, int]: 阶段名称到顺序索引的映射。
        """
        return {phase["name"]: idx for idx, phase in enumerate(schema["phases"])}

    def get_next_phase(self, schema: dict, current_phase: str) -> Optional[str]:
        """
        根据工作流 schema 获取下一个阶段的名称。

        Args:
            schema (dict): 工作流 schema 字典。
            current_phase (str): 当前阶段名称。

        Returns:
            Optional[str]: 下一个阶段名称，如果已是最后一个阶段则返回 None。
        """
        order = self.get_phase_order(schema)
        if current_phase not in order:
            # 如果当前阶段不在 schema 中，返回第一个阶段
            return schema["phases"][0]["name"] if schema["phases"] else None

        current_idx = order[current_phase]
        if current_idx + 1 < len(schema["phases"]):
            return schema["phases"][current_idx + 1]["name"]
        
        return None  # 已到最后

    def get_feature_status(self, feature_id: str, schema_name: str = "default") -> Dict[str, Any]:
        """
        获取指定特性的完整状态，包括当前阶段、下一阶段、完成度等。
        此方法依赖于 TaskOrchestrator 来聚合任务状态。

        Args:
            feature_id (str): 特性 ID。
            schema_name (str, optional): 使用的工作流名称 (默认 "default")。

        Returns:
            Dict[str, Any]: 包含特性状态信息的字典。
                - feature_id (str)
                - schema (str): schema name
                - workflow (str): workflow name
                - phases (Dict[str, str]): 阶段名称到其状态的映射
                - current_phase (Optional[str]): 最后一个完成的阶段
                - next_phase (Optional[str]): 推荐的下一个阶段
                - completed_count (int): 已完成的阶段数
                - total_count (int): 总阶段数
        """
        # --- 修改点：使用 self.task_orchestrator ---
        # tasks = list_task_states() # 旧的，直接调用函数
        tasks = self.task_orchestrator.list_task_states() # 新的，通过实例调用
        # --- 修改点结束 ---

        try:
            schema = self.load_workflow_schema(schema_name)
        except ValueError as e:
            raise e # 重新抛出，让调用者处理

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

        # 初始化所有 phase 状态
        for phase in schema["phases"]:
            status["phases"][phase["name"]] = "not-started"

        # 填充任务状态
        for task in tasks:
            if task.get("feature_id") == feature_id:
                phase_name = task["phase"]
                if phase_name in status["phases"]:
                    # 假设任务状态可以直接映射为阶段状态
                    # 或者可以根据需要进行转换 (e.g., confirmed -> completed)
                    task_status = task["status"]
                    # 简单映射示例 (可根据实际需求调整)
                    mapped_status = "completed" if task_status == TaskStatus.CONFIRMED.value else task_status
                    status["phases"][phase_name] = mapped_status

        # 找出当前进行中或最后完成的 phase
        ordered_phases = sorted(
            [p for p in schema["phases"] if p["name"] in status["phases"]],
            key=lambda x: phase_order[x["name"]]
        )

        # 找到最后一个“completed”的 phase
        completed_phases = [
            p["name"] for p in ordered_phases
            if status["phases"][p["name"]] == "completed"
        ]

        if completed_phases:
            last_completed = completed_phases[-1]
            status["current_phase"] = last_completed
            status["next_phase"] = self.get_next_phase(schema, last_completed)
        else:
            # 如果没有完成的阶段，则推荐第一个阶段
            first_phase = ordered_phases[0]["name"] if ordered_phases else None
            status["current_phase"] = None
            status["next_phase"] = first_phase

        status["completed_count"] = len(completed_phases)
        return status

    def determine_next_phase(self, current_phase: str, ai_response_content: str, context: Dict[str, Any]) -> Optional[str]:
        """
        基于AI响应内容和上下文智能决策下一阶段。
        这是一个基础实现，未来可以使用更复杂的规则引擎或机器学习。

        Args:
            current_phase (str): 当前（已完成）的阶段名称。
            ai_response_content (str): AI 生成的响应内容 (例如，来自任务 context['rendered'])。
            context (Dict[str, Any]): 任务的完整上下文信息。

        Returns:
            Optional[str]: 建议的下一个阶段名称。如果应遵循标准工作流，则返回 None。
        """
        # 简单的关键词匹配逻辑
        content_lower = ai_response_content.lower()

        # --- 示例规则：根据内容触发特殊阶段 ---
        # 注意：这些阶段 ('security_review', 'tech_spike', 'migration_plan')
        # 需要确保它们在你的工作流定义 (如 default.yaml) 中存在，
        # 或者你的系统能处理动态/未预定义的阶段。

        # 规则 1: 安全审查
        # 检查 "security" 和 "risk" 或 "impact" 是否同时出现
        if "security" in content_lower and ("risk" in content_lower or "impact" in content_lower):
            # 可以添加更复杂的条件，例如检查特定的分数或描述
            # if "high" in content_lower and ("security risk" in content_lower):
            return "security_review"

        # 规则 2: 技术预研
        if "new library" in content_lower or "significant architectural change" in content_lower:
            return "tech_spike"

        # 规则 3: 数据库迁移
        if "database migration" in content_lower:
            return "migration_plan"

        # --- 可以在这里添加更多规则 ---
        # 例如：
        # if "performance bottleneck" in content_lower:
        #     return "performance_optimization"
        # if "api integration" in content_lower and "third-party" in content_lower:
        #     return "api_integration_review"

        # 如果没有特殊规则匹配，默认返回 None，表示遵循标准工作流
        return None

    def recommend_next_phase(self, feature_id: str, schema_name: str = "default") -> Optional[Dict[str, Any]]:
        """
        为给定特性推荐下一个阶段，考虑智能决策。

        Args:
            feature_id (str): 特性 ID。
            schema_name (str, optional): 使用的工作流名称 (默认 "default")。

        Returns:
            Optional[Dict[str, Any]]: 包含推荐信息的字典，如果特性已完成则返回 None。
            字典包含：
                - 'phase' (str): 推荐的阶段名称。
                - 'reason' (str): 推荐原因。
                - 'source' (str): 推荐来源 ('standard' 或 'smart')。
                - 'current_phase' (str, optional): 当前最后一个完成的阶段。
        """
        # 1. 获取特性当前状态 (使用更新后的 get_feature_status)
        status = self.get_feature_status(feature_id, schema_name)

        # 2. 如果特性已完成，返回 None
        if not status.get("next_phase"):
            return None

        # 3. 获取标准工作流定义的下一个阶段
        standard_next_phase = status.get("next_phase")
        current_phase = status.get("current_phase") # 上一个完成的阶段

        # 4. 获取最后一个 confirmed 的任务 (用于智能决策)
        # 我们需要从 TaskOrchestrator 获取详细的任务数据
        all_tasks = self.task_orchestrator.list_task_states() # 获取所有任务摘要
        # 筛选出当前 feature 的已确认任务
        confirmed_tasks = [
            t for t in all_tasks
            if t["feature_id"] == feature_id and t["status"] == TaskStatus.CONFIRMED.value
        ]

        if not confirmed_tasks:
            # 如果没有 confirmed 的任务，则推荐标准的下一个阶段
            return {
                "phase": standard_next_phase,
                "reason": "No confirmed tasks found for feature, following standard workflow.",
                "source": "standard",
                "current_phase": current_phase
            }

        # 5. 假设 list_task_states 返回按时间倒序排列，取最新的 confirmed 任务
        #    或者显式按时间排序 (如果 list_task_states 不保证顺序)
        #    这里假设是倒序的，如 orchestrator.py 中实现的那样
        last_confirmed_task_summary = confirmed_tasks[0]
        last_confirmed_task_id = last_confirmed_task_summary["task_id"]

        # 6. 加载该任务的详细信息以获取 AI 响应
        last_task_data = self.task_orchestrator.load_task_state(last_confirmed_task_id)
        if not last_task_data:
            # 如果无法加载任务详情，回退到标准推荐
            return {
                "phase": standard_next_phase,
                "reason": f"Could not load details for last confirmed task {last_confirmed_task_id}, following standard workflow.",
                "source": "standard fallback",
                "current_phase": current_phase
            }

        ai_response_content = last_task_data.get("context", {}).get("rendered", "")
        task_context = last_task_data.get("context", {})

        # 7. 调用智能决策逻辑
        smart_next_phase = self.determine_next_phase(
            current_phase or last_task_data.get("phase", ""), # 提供当前阶段
            ai_response_content,
            task_context
        )

        # 8. 返回推荐结果
        if smart_next_phase and smart_next_phase != standard_next_phase:
            # 智能决策给出了不同的阶段
            return {
                "phase": smart_next_phase,
                "reason": f"Smart recommendation based on analysis of task {last_confirmed_task_id}'s output.",
                "source": "smart",
                "current_phase": current_phase
            }
        else:
            # 没有特殊推荐，遵循标准工作流
            return {
                "phase": standard_next_phase,
                "reason": "Following standard workflow sequence.",
                "source": "standard",
                "current_phase": current_phase
            }

# --- 为了兼容旧代码，可以保留这些函数作为模块级函数（可选）---
# --- 或者在 CLI 完全迁移后删除 ---
# def load_workflow_schema(name: str = "default"):
#     return WorkflowEngine().load_workflow_schema(name)
# 
# def get_phase_order(schema: dict):
#     return WorkflowEngine().get_phase_order(schema)
# 
# def get_next_phase(schema: dict, current_phase: str):
#     return WorkflowEngine().get_next_phase(schema, current_phase)
# 
# def get_feature_status(feature_id: str, schema_name: str = "default"):
#     return WorkflowEngine().get_feature_status(feature_id, schema_name)
