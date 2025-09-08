# chatflow/core/models.py
"""
ChatFlow 核心数据模型
定义了在工作流引擎和状态存储中使用的核心数据结构。
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum
import yaml

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

@dataclass
class WorkflowPhaseDefinition:
    """表示工作流定义中的一个阶段。"""
    name: str
    title: str
    template: str
    # 可以添加更多配置，如条件、超时等
    # condition: Optional[str] = None
    # timeout_seconds: Optional[int] = None

@dataclass
class WorkflowDefinition:
    """表示一个完整的工作流定义。"""
    name: str
    description: str
    phases: List[WorkflowPhaseDefinition]

    @classmethod
    def from_dict(cls, data: dict) -> 'WorkflowDefinition':
        """从字典（通常是 YAML 加载的结果）创建 WorkflowDefinition 实例。"""
        name = data.get("name", "unnamed")
        description = data.get("description", "")
        phases_data = data.get("phases", [])
        phases = [WorkflowPhaseDefinition(**pd) for pd in phases_data]
        return cls(name=name, description=description, phases=phases)



