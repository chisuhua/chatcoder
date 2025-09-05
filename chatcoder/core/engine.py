# chatcoder/core/engine.py
"""
ChatCoder 核心服务 - 工作流引擎 (WorkflowEngine)
负责加载工作流定义、管理特性状态和进行智能阶段推荐。
"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
from .state import list_task_states # 用于 get_feature_status

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

    def __init__(self):
        """
        初始化工作流引擎。
        """
        pass

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
        此方法依赖于 `list_task_states` 来聚合任务状态。

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
        # 注意：这里暂时直接调用旧的 list_task_states 函数
        # 在后续阶段，可以将其重构为通过 TaskOrchestrator 调用
        tasks = list_task_states() 
        
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
                    mapped_status = "completed" if task_status == "confirmed" else task_status
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
