# chatflow/core/state.py
"""
ChatFlow 核心接口 - 工作流状态存储 (IWorkflowStateStore)
定义了工作流实例状态持久化所需的标准接口。
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class IWorkflowStateStore(ABC):
    """
    抽象基类，用于定义工作流实例状态管理器的接口。
    所有具体的状态存储实现（如基于文件、数据库、内存等）都应继承此类。
    """

    @abstractmethod
    def save_state(self, instance_id: str, state_data: Dict[str, Any]) -> None:
        """
        保存工作流实例的状态。

        Args:
            instance_id (str): 工作流实例的唯一标识符。
            state_data (Dict[str, Any]): 包含工作流实例所有状态信息的字典。

        Raises:
            Exception: 如果保存失败，抛出相应异常。
        """
        pass

    @abstractmethod
    def load_state(self, instance_id: str) -> Optional[Dict[str, Any]]:
        """
        加载指定工作流实例的状态。

        Args:
            instance_id (str): 工作流实例的唯一标识符。

        Returns:
            Optional[Dict[str, Any]]: 工作流实例状态字典。如果实例不存在，返回 None。

        Raises:
            Exception: 如果加载失败（例如，数据损坏且无法修复），抛出相应异常。
        """
       pass
