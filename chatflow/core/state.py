# chatflow/core/state.py
"""
ChatFlow 核心接口 - 工作流状态存储 (IWorkflowStateStore)
定义了工作流实例状态持久化所需的标准接口。
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class IWorkflowStateStore(ABC):
    """
    抽象基类，用于定义工作流实例状态管理器的接口。
    所有具体的状态存储实现（如基于文件、数据库、内存等）都应继承此类。
    """

    @abstractmethod
    def save_state(self, instance_id: str, state_data: Dict[str, Any]) -> None:
        """ 保存工作流实例的状态。 """
        pass

    @abstractmethod
    def load_state(self, instance_id: str) -> Optional[Dict[str, Any]]:
        """ 加载指定工作流实例的状态。 """
        pass

    # --- 新增：为支持按 feature 查询实例 ---
    @abstractmethod
    def list_instances_by_feature(self, feature_id: str) -> List[Dict[str, Any]]:
        """
        根据特性 ID 列出所有相关的工作流实例状态。
        这对于 get_feature_status 和 recommend_next_phase 等方法至关重要。
        """
        pass

