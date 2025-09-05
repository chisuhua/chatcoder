# chatcoder/core/models.py
"""
定义 ChatCoder 核心数据结构，例如 Change 和 ChangeSet。
这些模型用于在 AI 响应解析、文件变更应用和任务状态管理之间传递数据。
"""
from enum import Enum
from typing import TypedDict, Optional, List


class Change(TypedDict):
    """
    描述对单个文件的一次变更操作。
    
    Attributes:
        file_path (str): 目标文件的相对路径 (e.g., "src/my_module.py")。
        operation (str): 操作类型: "create", "modify"。
        new_content (str): 新的文件内容 (用于 create 和 modify)。
        description (Optional[str]): (可选) 对此变更的简短描述 (来自AI输出或上下文)。
    """
    file_path: str
    operation: str  # Expected to be "create" or "modify" initially
    new_content: str
    description: Optional[str]


class ChangeSet(TypedDict):
    """
    描述一次 AI 响应中包含的所有文件变更。
    
    Attributes:
        changes (List[Change]): 变更列表。
        source_task_id (Optional[str]): 生成此变更集的 ChatCoder 任务 ID。
    """
    changes: List[Change]
    source_task_id: Optional[str]

class TaskStatus(Enum):
    """
    定义 ChatCoder 任务的可能状态。
    """
    PENDING = "pending"
    AI_RESPONSE_RECEIVED = "ai_response_received"
    AWAITING_REVIEW = "awaiting_review"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    COMPLETED = "completed" # 可以与 CONFIRMED 同义，或用于更复杂的流程

    @classmethod
    def is_valid_status(cls, status_str: str) -> bool:
        """
        检查给定的字符串是否是有效的任务状态。
        """
        return status_str in cls._value2member_map_

    @classmethod
    def from_string(cls, status_str: str):
        """
        从字符串创建 TaskStatus 枚举实例。
        如果字符串无效，则返回 None 或抛出异常。
        """
        # 方法1: 返回 None (更安全)
        return cls._value2member_map_.get(status_str, None)
        
        # 方法2: 抛出异常 (更严格)
        # try:
        #     return cls(status_str)
        # except ValueError:
        #     raise ValueError(f"'{status_str}' is not a valid TaskStatus") from None

# ... (文件末尾) ...
