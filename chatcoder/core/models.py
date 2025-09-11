# chatcoder/core/models.py
"""
定义 ChatCoder 核心数据结构，例如 Change 和 ChangeSet。
这些模型用于在 AI 响应解析、文件变更应用和任务状态管理之间传递数据。
[注意] TaskStatus 枚举已被移除，状态管理由 chatflow 负责。
"""

from typing import TypedDict, Optional, List

class Change(TypedDict):
    """
    描述对单个文件的一次变更操作。
    """
    file_path: str
    operation: str  # Expected to be "create" or "modify" initially
    new_content: str
    description: Optional[str]

class ChangeSet(TypedDict):
    """
    描述一次 AI 响应中包含的所有文件变更。
    """
    changes: List[Change]
    source_task_id: Optional[str]

# --- 移除 TaskStatus 枚举 ---
# class TaskStatus(Enum): ...
# 因为状态管理已由 chatflow.core.models.WorkflowInstanceStatus 负责。
