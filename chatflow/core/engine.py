# chatflow/core/engine.py
"""
ChatFlow 核心接口 - 工作流引擎 (IWorkflowEngine)
定义了工作流引擎应提供的核心能力。
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
# 假设核心数据结构定义在 models.py 中
# from .models import WorkflowDefinition, WorkflowInstanceStatus, ContextRequest

class IWorkflowEngine(ABC):
    """
    抽象基类，定义工作流引擎的接口。
    """

    @abstractmethod
    def load_workflow_schema(self, name: str = "default") -> dict:
        """
        加载指定名称的工作流模式（YAML 定义）。

        Args:
            name (str, optional): 工作流名称 (默认 "default")。

        Returns:
            dict: 解析后的工作流 schema 字典。

        Raises:
            ValueError: 如果指定的工作流文件未找到。
        """
        pass

    @abstractmethod
    def get_feature_status(self, feature_id: str, schema_name: str = "default") -> Dict[str, Any]:
        """
        获取指定特性的完整状态。

        Args:
            feature_id (str): 特性 ID。
            schema_name (str, optional): 使用的工作流名称 (默认 "default")。

        Returns:
            Dict[str, Any]: 包含特性状态信息的字典。
                通常包括：
                - feature_id (str)
                - schema (str): schema name
                - workflow (str): workflow name
                - phases (Dict[str, str]): 阶段名称到其状态的映射
                - current_phase (Optional[str]): 最后一个完成的阶段
                - next_phase (Optional[str]): 推荐的下一个阶段
                - completed_count (int): 已完成的阶段数
                - total_count (int): 总阶段数
        """
        pass

    @abstractmethod
    def recommend_next_phase(self, feature_id: str, schema_name: str = "default") -> Optional[Dict[str, Any]]:
        """
        为给定特性推荐下一个阶段。

        Args:
            feature_id (str): 特性 ID。
            schema_name (str, optional): 使用的工作流名称 (默认 "default")。

        Returns:
            Optional[Dict[str, Any]]: 包含推荐信息的字典，如果特性已完成则返回 None。
                字典通常包括：
                - 'phase' (str): 推荐的阶段名称。
                - 'reason' (str): 推荐原因。
                - 'source' (str): 推荐来源 ('standard' 或 'smart')。
                - 'current_phase' (str, optional): 当前最后一个完成的阶段。
        """
        pass

    # 可以在这里添加更多抽象方法，例如 determine_next_phase
    # @abstractmethod
    # def determine_next_phase(self, current_phase: str, ai_response_content: str, context: Dict[str, Any]) -> Optional[str]:
    #     """
    #     基于AI响应内容和上下文智能决策下一阶段。
    #
    #     Args:
    #         current_phase (str): 当前（已完成）的阶段名称。
    #         ai_response_content (str): AI 生成的响应内容。
    #         context (Dict[str, Any]): 任务的完整上下文信息。
    #
    #     Returns:
    #         Optional[str]: 建议的下一个阶段名称。如果应遵循标准工作流，则返回 None。
    #     """
    #     pass

    # 未来可能的接口方法 (为演进预留)
    # @abstractmethod
    # def start_workflow_instance(self, workflow_definition: 'WorkflowDefinition', initial_context: 'ContextRequest') -> str:
    #     """
    #     启动一个新的工作流实例。
    #
    #     Args:
    #         workflow_definition (WorkflowDefinition): 工作流定义。
    #         initial_context (ContextRequest): 初始上下文。
    #
    #     Returns:
    #         str: 新创建的工作流实例 ID。
    #     """
    #     pass

    # @abstractmethod
    # def get_workflow_instance_status(self, instance_id: str) -> 'WorkflowInstanceStatus':
    #     """
    #     获取工作流实例的当前状态。
    #
    #     Args:
    #         instance_id (str): 工作流实例 ID。
    #
    #     Returns:
    #         WorkflowInstanceStatus: 工作流实例状态。
    #     """
    #     pass
