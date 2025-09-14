# chatflow/core/models.py
"""
ChatFlow 核心数据模型
定义了在工作流引擎和状态存储中使用的核心数据结构。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional
from enum import Enum
import yaml

class WorkflowStatus(Enum):
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"

@dataclass
class HistoryEntry:
    event_type: str  # workflow_started, phase_started, phase_completed, etc.
    phase: str
    task: str
    timestamp: float
    #started_at: float
    #ended_at: Optional[float] = None
    #status: str = "running"  # running, completed, failed
    data: Dict[str, Any] = field(default_factory=dict)  # trigger_data_snapshot, metrics等

@dataclass
class TaskExecutionRecord:
    phase_name: str
    status: str
    started_at: float
    ended_at: Optional[float] = None
    prompt_checksum: str = ""
    response_checksum: str = ""
    artifact_paths: Dict[str, str] = field(default_factory=dict)

@dataclass
class WorkflowState:
    """内存中完整运行时状态"""
    instance_id: str
    feature_id: str
    workflow_name: str
    current_phase: str
    variables: Dict[str, Any]
    status: WorkflowStatus # 使用 WorkflowStatus 枚举
    history: List[HistoryEntry] = field(default_factory=list)
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    updated_at: float = field(default_factory=lambda: datetime.now().timestamp()) # 修正拼写: t imestamp -> timestamp
    meta: Dict[str, Any] = field(default_factory=dict)
    automation_level: int = 60  # 0-100

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkflowState':
        """
        从字典创建 WorkflowState 实例，正确处理 status 和 history 字段。
        """
        data = data.copy()

        status_str = data.get("status")
        if isinstance(status_str, str):
            matched_status = None
            for status_member in WorkflowStatus:
                if status_member.value.strip() == status_str.strip():
                    matched_status = status_member
                    break
            if matched_status is None:
                print(f"Warning: Unknown status string '{status_str}', defaulting to WorkflowStatus.CREATED")
                data["status"] = WorkflowStatus.CREATED
            else:
                data["status"] = matched_status
        elif not isinstance(status_str, WorkflowStatus):
            data["status"] = WorkflowStatus.CREATED

        raw_history = data.get("history", [])
        if raw_history and isinstance(raw_history, list) and isinstance(raw_history[0], dict):
            converted_history = [HistoryEntry(**event_dict) for event_dict in raw_history]
            data["history"] = converted_history

        return cls(**data)

@dataclass
class WorkflowStatusInfo:
    """对外暴露的精简状态"""
    instance_id: str
    status: str  # "running", "completed"
    progress: float  # 0.0 - 1.0
    current_phase: str
    feature_id: str
    created_at: float
    updated_at: float
    depth: int = 0  # 递归深度 (v2预留)

# 返回值对象
@dataclass
class WorkflowStartResult:
    instance_id: str
    initial_phase: str
    created_at: float
