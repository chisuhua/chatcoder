# chatcoder/core/state.py
"""
任务状态持久化模块

提供任务状态的保存、加载与列表查询功能。
每个任务生成唯一 ID，状态保存至 .chatcoder/tasks/${task_id}.json
"""
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

# 任务状态存储目录
TASKS_DIR = Path(".chatcoder") / "tasks"


def ensure_tasks_dir() -> None:
    """确保任务目录存在"""
    TASKS_DIR.mkdir(parents=True, exist_ok=True)


def generate_task_id() -> str:
    """
    生成任务唯一 ID，格式: tsk_{unix_timestamp}_{random}
    示例: tsk_1725293840_5a3b8c
    """
    timestamp = int(datetime.now().timestamp())
    random_suffix = uuid.uuid4().hex[:6]
    return f"tsk_{timestamp}_{random_suffix}"


def get_task_file_path(task_id: str) -> Path:
    """获取任务状态文件路径"""
    return TASKS_DIR / f"{task_id}.json"


def save_task_state(
    task_id: str,
    template: str,
    description: str,
    context: Dict[str, Any]
) -> None:
    """
    保存任务状态到本地文件

    Args:
        task_id: 任务唯一ID
        template: 使用的模板路径
        description: 任务描述
        context: 项目上下文快照
    """
    ensure_tasks_dir()

    state_data = {
        "task_id": task_id,
        "template": template,
        "description": description,
        "context": context,
        "created_at": datetime.now().isoformat(),
        "created_at_str": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    task_file = get_task_file_path(task_id)
    with open(task_file, "w", encoding="utf-8") as f:
        json.dump(state_data, f, ensure_ascii=False, indent=2)

    # 可选：打印提示
    # from chatcoder.utils.console import info
    # info(f"任务状态已保存: {task_file}")


def load_task_state(task_id: str) -> Optional[Dict[str, Any]]:
    """
    加载指定任务的状态

    Args:
        task_id: 任务ID

    Returns:
        任务状态字典，若不存在则返回 None
    """
    task_file = get_task_file_path(task_id)
    if not task_file.exists():
        return None

    try:
        with open(task_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        # 可选：记录错误
        # from chatcoder.utils.console import error
        # error(f"读取任务状态失败: {e}")
        return None


def list_task_states() -> List[Dict[str, Any]]:
    """
    列出所有已保存的任务状态（按时间倒序）

    Returns:
        任务状态列表，每个元素包含 task_id, template, description, created_at_str
    """
    if not TASKS_DIR.exists():
        return []

    tasks = []
    for json_file in TASKS_DIR.glob("*.json"):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                # 仅提取必要字段用于列表展示
                tasks.append({
                    "task_id": data["task_id"],
                    "template": data["template"],
                    "description": data["description"],
                    "created_at_str": data["created_at_str"]
                })
        except (json.JSONDecodeError, KeyError, IOError):
            continue  # 跳过损坏的文件

    # 按时间倒序排序
    return sorted(tasks, key=lambda x: x["created_at_str"], reverse=True)


# ------------------------------
# 附加工具（可选）
# ------------------------------

def clear_all_tasks() -> int:
    """
    清除所有任务状态（谨慎使用）

    Returns:
        删除的文件数量
    """
    if not TASKS_DIR.exists():
        return 0

    count = 0
    for file in TASKS_DIR.glob("*.json"):
        file.unlink()
        count += 1
    return count


def get_latest_task() -> Optional[Dict[str, Any]]:
    """
    获取最新创建的任务

    Returns:
        最新任务状态，若无则返回 None
    """
    tasks = list_task_states()
    return tasks[0] if tasks else None
