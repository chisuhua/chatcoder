# chatcoder/core/state.py
"""
任务状态持久化模块
"""
import re
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from .workflow import load_workflow_schema, get_phase_order

# 任务状态存储目录
TASKS_DIR = Path(".chatcoder") / "tasks"
TASKS_DIR.mkdir(parents=True, exist_ok=True)


def get_tasks_dir() -> Path:
    """确保 TASKS_DIR 存在并返回"""
    TASKS_DIR.mkdir(parents=True, exist_ok=True)
    return TASKS_DIR

def generate_feature_id(description: str) -> str:
    """根据描述生成简洁的 feature_id"""
    # 移除特殊字符，只保留字母、数字、中文、空格
    cleaned = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff\s]", "", description.lower())
    # 转为单词列表
    words = cleaned.split()
    # 取前 4 个词，连接
    short_words = "_".join(words[:4])
    prefix = "feat"
    if not short_words:
        return f"{prefix}_"
    return f"{prefix}_{short_words}"

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
    context: Dict[str, Any],
    feature_id: str = None,
    phase: str = None,  # analyze/design/implement/test/summary
    status: str = "pending",
    workflow: str = "default"
) -> None:
    """保存任务状态到 JSON 文件"""
    ensure_tasks_dir()
    # 使用传入的 feature_id 或生成一个
    final_feature_id = feature_id or generate_feature_id(description)

    # 动态加载 workflow schema 来获取 phase_order
    try:
        schema = load_workflow_schema(workflow)
        phase_order_map = get_phase_order(schema)
        phase_order = phase_order_map.get(phase.lower(), 99)  # fallback to 99
    except Exception:
        # 失败时 fallback 到默认顺序（兼容旧代码）
        PHASE_ORDER = {
            "init": 0,
            "analyze": 1,
            "design": 2,
            "code": 3,
            "test": 4,
            "review": 5,
            "patch": 6,
            "deploy": 7,
            "done": 8,
        }
        phase_order = PHASE_ORDER.get(phase.lower(), 99)

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
        "status": status
    }

    task_file = get_task_file_path(task_id)
    task_file.write_text(json.dumps(state_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ 任务已保存: {task_file}")


def load_task_state(task_id: str) -> Optional[Dict[str, Any]]:
    """
    加载指定任务的状态
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
                    "feature_id": data["feature_id"],
                    "phase": data["phase"],
                    "template": data["template"],
                    "status": data["status"],
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
