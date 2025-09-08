# chatflow/core/models.py
"""
ChatFlow 核心数据模型
定义了在工作流引擎和状态存储中使用的核心数据结构。
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum

class WorkflowInstanceStatus(Enum):
    """
    定义工作流实例的可能状态。
    """
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class WorkflowInstanceState:
    """
    描述一个工作流实例的完整状态。
    由 ChatFlow 内部管理和持久化。
    """
    instance_id: str
    feature_id: str # 关联到 ChatCoder 的 feature_id
    workflow_name: str # 使用的工作流定义名称 (e.g., "default")
    
    current_phase: Optional[str] = None
    history: List[Dict[str, Any]] = field(default_factory=list) # 阶段执行历史
    variables: Dict[str, Any] = field(default_factory=dict) # 工作流实例级别变量/上下文
    
    status: WorkflowInstanceStatus = WorkflowInstanceStatus.CREATED
    
    created_at: str = ""
    updated_at: str = ""
    
    # 可以根据需要添加更多字段，例如：
    # metadata: Dict[str, Any] = field(default_factory=dict) # 用户或系统元数据

# --- 保留原有的 TaskStatus 枚举占位符或导入 ---
# 如果 chatflow 内部也需要类似的任务状态概念，可以保留或重新定义
# 但为了避免与 ChatCoder 的 TaskStatus 混淆，最好使用不同的名称或作用域
# 例如，专门用于 ChatFlow 内部任务（如果有的话）的状态
# class ChatFlowTaskStatus(Enum):
#     PENDING = "pending"
#     IN_PROGRESS = "in_progress"
#     DONE = "done"
