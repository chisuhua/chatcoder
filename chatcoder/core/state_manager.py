# chatcoder/core/state_manager.py
"""
ChatCoder 状态管理器抽象基类
定义了任务状态持久化所需的标准接口。
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, List, Optional


class StateManager(ABC):
    """
    抽象基类，用于定义任务状态管理器的接口。
    所有具体的状态管理实现（如基于文件、数据库等）都应继承此类。
    """

    @abstractmethod
    def save_task_state(self, task_id: str, task_data: Dict[str, Any]) -> None:
        """
        保存任务状态。

        Args:
            task_id (str): 任务的唯一标识符。
            task_data (Dict[str, Any]): 包含任务所有状态信息的字典。
        
        Raises:
            Exception: 如果保存失败，抛出相应异常。
        """
        pass

    @abstractmethod
    def load_task_state(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        加载指定任务的状态。

        Args:
            task_id (str): 任务的唯一标识符。

        Returns:
            Optional[Dict[str, Any]]: 任务状态字典。如果任务不存在，返回 None。
        
        Raises:
            Exception: 如果加载失败（例如，文件损坏且无法修复），抛出相应异常。
        """
        pass

    @abstractmethod
    def list_task_states(self) -> List[Dict[str, Any]]:
        """
        列出所有已保存的任务状态摘要。

        Returns:
            List[Dict[str, Any]]: 一个包含所有任务状态摘要的列表。
                                 摘要应至少包含 task_id, feature_id, phase, status 等关键字段
                                 以便于列表和查询。
        
        Raises:
            Exception: 如果列出失败，抛出相应异常。
        """
        pass

    @abstractmethod
    def get_task_file_path(self, task_id: str) -> Path:
        """
        获取任务状态文件的完整路径（如果适用）。
        这个方法主要为需要直接访问文件的场景（如备份、手动检查）提供便利。

        Args:
            task_id (str): 任务的唯一标识符。

        Returns:
            Path: 任务状态文件的 Path 对象。
        """
        pass
