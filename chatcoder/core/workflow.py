# chatcoder/core/workflow.py
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List

PROJECT_ROOT= Path(__file__).parent.parent.parent
TEMPLATES_DIR = PROJECT_ROOT / "ai-prompts" 

def get_workflow_path() -> Path:
    """获取任务状态文件路径"""
    return TEMPLATES_DIR / "workflows"


def load_workflow_schema(name: str = "default") -> dict:
    """加载工作流模板，支持自定义 phase 顺序和配置"""
    # 尝试从 workflows 目录加载
    custom_path = TEMPLATES_DIR / "workflows" / f"{name}.yaml"
    if custom_path.exists():
        return yaml.safe_load(custom_path.read_text(encoding="utf-8"))

    raise ValueError(f"workflows schema not foud: {name}")


def get_phase_order(schema: dict) -> Dict[str, int]:
    """从 schema 中提取 phase 到 order 的映射"""
    return {phase["name"]: idx for idx, phase in enumerate(schema["phases"])}


def get_next_phase(schema: dict, current_phase: str) -> Optional[str]:
    """根据 schema 获取下一个 phase"""
    order = get_phase_order(schema)
    if current_phase not in order:
        return schema["phases"][0]["name"]  # 返回第一个
    current_idx = order[current_phase]
    if current_idx + 1 < len(schema["phases"]):
        return schema["phases"][current_idx + 1]["name"]
    return None  # 已到最后


def get_feature_status(feature_id: str, schema_name: str = "default") -> Dict[str, Any]:
    """获取 feature 的完整状态，使用模板定义的 phases"""
    from .state import list_task_states

    tasks = list_task_states()
    try:
        schema = load_workflow_schema(schema_name)
    except ValueError as e:
        raise e

    phase_order = get_phase_order(schema)

    status = {
        "feature_id": feature_id,
        "schema": schema["name"],
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
                status["phases"][phase_name] = task["status"]

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
        status["next_phase"] = get_next_phase(schema, last_completed)
    else:
        first_phase = ordered_phases[0]["name"]
        status["current_phase"] = None
        status["next_phase"] = first_phase

    status["completed_count"] = len(completed_phases)
    return status
