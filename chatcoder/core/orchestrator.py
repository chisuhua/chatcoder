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
from .state_manager import StateManager # 为未来扩展预留接口
from .models import TaskStatus

from .workflow import load_workflow_schema, get_phase_order

# 任务状态存储目录 (与 state.py 保持一致)
TASKS_DIR = Path(".chatcoder") / "tasks"

# 确保 TASKS_DIR 存在的函数可以作为类的静态方法或独立辅助函数
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

    def __init__(self): # state_manager: Optional[StateManager] = None):
        """
        初始化任务编排器。
        # TODO: 未来可以支持注入不同的状态管理器（如数据库）
        # self.state_manager = state_manager
        """
        self.state_manager = StateManager
        pass

    def generate_feature_id(self, description: str) -> str:
        """
        根据描述生成简洁的 feature_id。
        
        Args:
            description (str): 功能描述。
            
        Returns:
            str: 生成的 feature_id。
        """
        # 移除特殊字符，只保留字母、数字、中文、空格
        cleaned = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff\s]", " ", description.lower())
        # 转为单词列表
        words = cleaned.split()
        # 取前 4 个词，连接
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
        
        Returns:
            str: 生成的任务 ID。
        """
        timestamp = int(datetime.now().timestamp())
        random_suffix = uuid.uuid4().hex[:6]
        return f"tsk_{timestamp}_{random_suffix}"

    def _get_phase_order_for_workflow(self, workflow: str, phase: str) -> int:
        """
        内部辅助方法：根据工作流名称和阶段名称获取其顺序。
        """
        try:
            schema = load_workflow_schema(workflow)
            phase_order_map = get_phase_order(schema)
            return phase_order_map.get(phase.lower(), 99)  # fallback to 99
        except Exception:
            # 失败时 fallback 到默认顺序（兼容旧代码）
            PHASE_ORDER = {
                "init": 0,
                "analyze": 1,
                "design": 2,
                "code": 3, # 注意：旧代码用 code, 新工作流可能用 implement
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

        Args:
            task_id (str): 任务唯一 ID。
            template (str): 使用的模板名称。
            description (str): 任务描述。
            context (Dict[str, Any]): 任务上下文（如渲染后的提示词）。
            feature_id (str, optional): 关联的特性 ID。如果未提供，将根据描述生成。
            phase (str, optional): 任务所处阶段 (e.g., analyze, design)。
            status (str, optional): 任务状态 (默认 "pending")。
            workflow (str, optional): 使用的工作流名称 (默认 "default")。
        """
        _ensure_tasks_dir()
        
        # 使用传入的 feature_id 或生成一个
        final_feature_id = feature_id or self.generate_feature_id(description)

        # 尝试将传入的 status 字符串转换为 TaskStatus 枚举
        if isinstance(status, str):
            if TaskStatus.is_valid_status(status):
                status_value = status # 已经是有效的字符串
            else:
                # 可选：记录警告或抛出异常
                # print(f"⚠️  Invalid status '{status}', defaulting to PENDING.")
                status_value = TaskStatus.PENDING.value
        elif isinstance(status, TaskStatus):
            status_value = status.value # 从枚举获取字符串值
        else:
            # 处理意外类型
            # print(f"⚠️  Invalid status type '{type(status)}', defaulting to PENDING.")
            status_value = TaskStatus.PENDING.value

        # 动态加载 workflow schema 来获取 phase_order
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
            # 可以在这里添加 confirmed_at 等字段，如果需要的话
            # "confirmed_at": None,
            # "confirmed_at_str": None,
        }

        task_file = _get_task_file_path(task_id)
        task_file.write_text(json.dumps(state_data, ensure_ascii=False, indent=2), encoding="utf-8")
        # 注意：为了保持与原逻辑一致，这里打印。未来可考虑用日志替代。
        # print(f"✅ 任务已保存: {task_file}") 

    def load_task_state(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        加载指定任务的状态。

        Args:
            task_id (str): 任务 ID。
            
        Returns:
            Optional[Dict[str, Any]]: 任务状态字典，如果文件不存在或加载失败则返回 None。
        """
        task_file = _get_task_file_path(task_id)
        if not task_file.exists():
            return None

        try:
            with open(task_file, "r", encoding="utf-8") as f:
                return json.load(f)
                # --- 可选增强: 验证加载的状态 ---
                # loaded_status = data.get("status")
                # if loaded_status and not TaskStatus.is_valid_status(loaded_status):
                #     print(f"⚠️  Loaded task {task_id} has invalid status '{loaded_status}'.")
                # --- 结束可选增强 ---
        except (json.JSONDecodeError, IOError) as e:
            # 可选：记录错误日志
            # from chatcoder.utils.console import error
            # error(f"读取任务状态失败: {e} ")
            return None

    def list_task_states(self) -> List[Dict[str, Any]]:
        """
        列出所有已保存的任务状态（按时间倒序）。

        Returns:
            List[Dict[str, Any]]: 任务状态列表。
        """
        tasks_dir = _get_tasks_dir()
        if not tasks_dir.exists():
            return []

        tasks = []
        for json_file in tasks_dir.glob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # 仅提取必要字段用于列表展示
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
                # 跳过损坏的文件
                continue 

        # 按时间倒序排序
        return sorted(tasks, key=lambda x: x["created_at_str"], reverse=True)

    def get_latest_task(self) -> Optional[Dict[str, Any]]:
        """
        获取最新创建的任务。

        Returns:
            Optional[Dict[str, Any]]: 最新任务状态，若无则返回 None。
        """
        tasks = self.list_task_states()
        return tasks[0] if tasks else None

    # 为 CLI 提供便捷访问路径的方法
    def get_task_file_path(self, task_id: str) -> Path:
        """
        获取任务状态文件的完整路径。

        Args:
            task_id (str): 任务 ID。
            
        Returns:
            Path: 任务文件的 Path 对象。
        """
        return _get_task_file_path(task_id)

# --- 为了兼容旧代码，可以保留这些函数作为模块级函数（可选）---
# --- 或者在 CLI 完全迁移后删除 ---
# def generate_task_id():
#     return TaskOrchestrator().generate_task_id()
# 
# def save_task_state(...):
#     return TaskOrchestrator().save_task_state(...)
# 
# def load_task_state(...):
#     return TaskOrchestrator().load_task_state(...)
# 
# def list_task_states():
#     return TaskOrchestrator().list_task_states()
# 
# def get_latest_task():
#     return TaskOrchestrator().get_latest_task()
# 
# def get_task_file_path(task_id: str) -> Path:
#     return TaskOrchestrator().get_task_file_path(task_id)
