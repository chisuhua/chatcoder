# chatflow/core/state.py
"""
ChatFlow 核心接口 - 工作流状态存储 (IWorkflowStateStore)
定义了工作流实例状态持久化所需的标准接口。
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class IWorkflowStateStore(ABC):
    @abstractmethod
    def save_state(self, instance_id: str, state_data: Dict[str, Any]) -> None:
        pass

    @abstractmethod
    def load_state(self, instance_id: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def list_instances_by_feature(self, feature_id: str) -> List[str]:
        pass

    @abstractmethod
    def save_task_artifacts(
        self,
        feature_id: str,
        instance_id: str,
        phase_name: str,
        task_record_data: Dict,
        prompt_content: str,
        ai_response_content: str
    ):
        raise NotImplementedError


    @abstractmethod
    def get_current_task_id_for_feature(self, feature_id: str) -> Optional[str]:
        """根据 feature_id 获取当前活动（非完成）任务的 instance_id。"""
        pass

    @abstractmethod
    def list_features(self) -> List[str]:
        """获取所有已知的 feature_id 列表。"""
        pass


