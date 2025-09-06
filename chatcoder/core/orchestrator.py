# chatcoder/core/orchestrator.py
"""
ChatCoder 核心服务 - 任务编排器 (TaskOrchestrator)
负责任务的创建、加载、保存、查询等生命周期管理。
"""

import re
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from .state_manager import StateManager
from .models import TaskStatus

TASKS_DIR = Path(".chatcoder") / "tasks"

def _ensure_tasks_dir() -> None:
    """确保任务目录存在"""
    TASKS_DIR.mkdir(parents=True, exist_ok=True)

def _get_tasks_dir() -> Path:
    """获取任务目录路径"""
    _ensure_tasks_dir()
    return TASKS_DIR

def _get_task_file_path(task_id: str) -> Path:
    """获取任务状态文件路径"""
    return _get_tasks_dir() / f"{task_id}.json"


class TaskOrchestrator:
    """
    任务编排器，负责管理 ChatCoder 任务的完整生命周期。
    """

    def __init__(self):
        """
        初始化任务编排器。
        """
        pass

    def generate_feature_id(self, description: str) -> str:
        """
        根据描述生成简洁的 feature_id。
        """
        cleaned = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff\s]", " ", description.lower())
        words = cleaned.split()
        short_words = "_".join(words[:4])
        prefix = "feat"
        if not short_words:
            return f"{prefix}_"
        return f"{prefix}_{short_words}"

    def generate_task_id(self) -> str:
        """
        生成任务唯一 ID。
        格式: tsk_{unix_timestamp}_{random}
        示例: tsk_1725293840_5a3b8c
        """
        timestamp = int(datetime.now().timestamp())
        random_suffix = uuid.uuid4().hex[:6]
        return f"tsk_{timestamp}_{random_suffix}"

    def _get_phase_order_for_workflow(self, workflow: str, phase: str) -> int:
        """
        内部辅助方法：根据工作流名称和阶段名称获取其顺序。
        """
        try:
            from .engine import WorkflowEngine
            temp_engine = WorkflowEngine()
            schema = temp_engine.load_workflow_schema(workflow)
            phase_order_map = temp_engine.get_phase_order(schema)
            return phase_order_map.get(phase.lower(), 99)
        except Exception:
            PHASE_ORDER = {
                "init": 0,
                "analyze": 1,
                "design": 2,
                "code": 3,
                "implement": 3,
                "test": 4,
                "review": 5,
                "patch": 6,
                "deploy": 7,
                "done": 8,
                "summary": 9,
            }
            return PHASE_ORDER.get(phase.lower(), 99)

    def save_task_state(
        self,
        task_id: str,
        template: str,
        description: str,
        context: Dict[str, Any],
        feature_id: str = None,
        phase: str = None,
        status: str = TaskStatus.PENDING.value,
        workflow: str = "default"
    ) -> None:
        """
        保存任务状态到 JSON 文件。
        """
        _ensure_tasks_dir()
        
        final_feature_id = feature_id or self.generate_feature_id(description)

        if isinstance(status, str):
            if TaskStatus.is_valid_status(status):
                status_value = status
            else:
                status_value = TaskStatus.PENDING.value
        elif isinstance(status, TaskStatus):
            status_value = status.value
        else:
            status_value = TaskStatus.PENDING.value

        phase_order = self._get_phase_order_for_workflow(workflow, phase)

        state_data = {
            "task_id": task_id,
            "template": template,
            "feature_id": final_feature_id,
            "description": description,
            "context": context,
            "phase": phase,
            "phase_order": phase_order,
            "workflow": workflow,
            "created_at": datetime.now().isoformat(),
            "created_at_str": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status": status_value,
        }

        task_file = _get_task_file_path(task_id)
        task_file.write_text(json.dumps(state_data, ensure_ascii=False, indent=2), encoding="utf-8")

    def load_task_state(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        加载指定任务的状态。
        """
        task_file = _get_task_file_path(task_id)
        if not task_file.exists():
            return None

        try:
            with open(task_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            return None

    def list_task_states(self) -> List[Dict[str, Any]]:
        """
        列出所有已保存的任务状态（按时间倒序）。
        """
        tasks_dir = _get_tasks_dir()
        if not tasks_dir.exists():
            return []

        tasks = []
        for json_file in tasks_dir.glob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    tasks.append({
                        "task_id": data["task_id"],
                        "feature_id": data["feature_id"],
                        "phase": data["phase"],
                        "template": data["template"],
                        "status": data["status"],
                        "description": data["description"],
                        "created_at_str": data["created_at_str"]
                    })
            except (json.JSONDecodeError, KeyError, IOError):
                continue 

        return sorted(tasks, key=lambda x: x["created_at_str"], reverse=True)

    def get_latest_task(self) -> Optional[Dict[str, Any]]:
        """
        获取最新创建的任务。
        """
        tasks = self.list_task_states()
        return tasks[0] if tasks else None

    def get_task_file_path(self, task_id: str) -> Path:
        """
        获取任务状态文件的完整路径。
        """
        return _get_task_file_path(task_id)

    def get_tasks_dir(self) -> Path:
        return _get_tasks_dir()
