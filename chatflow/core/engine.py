# chatflow/core/engine.py
"""
ChatFlow 核心接口 - 工作流引擎 (IWorkflowEngine)
定义了工作流引擎应提供的核心能力。
"""

from typing import Dict, Any, Optional, List
from dataclasses import asdict
from abc import ABC, abstractmethod
from ..storage.state import IWorkflowStateStore
from .models import WorkflowStartResult, WorkflowState, HistoryEntry

class IWorkflowEngine(ABC):
    """工作流引擎接口"""
    def __init__(self, state_store: IWorkflowStateStore):
        self.state_store = state_store

    @abstractmethod
    def get_feature_status(self, feature_id: str, schema_name: str = "default") -> Dict[str, Any]:
        pass

    @abstractmethod
    def start_workflow_instance(self, workflow_schema: Dict[str, Any], initial_context: Dict[str, Any], feature_id: str, meta: Optional[Dict]) -> WorkflowStartResult:
        pass

    @abstractmethod
    def trigger_next_step(self, instance_id: str, trigger_data: Optional[Dict] = None, dry_run: bool = False, meta: Optional[Dict] = None) -> WorkflowState:
        pass


    @abstractmethod
    def get_workflow_state(self, instance_id: str) -> Optional[WorkflowState]: # 添加 instance_id 参数
        pass

    @abstractmethod
    def get_workflow_history(self) -> List[HistoryEntry]:
        pass
