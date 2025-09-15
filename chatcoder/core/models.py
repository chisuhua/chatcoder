# chatcoder/core/models.py
"""
定义 ChatCoder 核心数据结构，例如 Change 和 ChangeSet。
这些模型用于在 AI 响应解析、文件变更应用和任务状态管理之间传递数据。
"""

from typing import TypedDict, Optional, List

class Change(TypedDict):
    """ 描述对单个文件的一次变更操作。 """
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
