# chatcontext/core/manager.py
"""
ChatContext 核心接口 - 上下文管理器 (IContextManager)
定义了上下文管理器应提供的核心能力。
负责协调 ContextProviders，处理 ContextRequests，并返回最终的上下文。
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from .models import ContextRequest, ProvidedContext # ContextPipelineConfig (如果需要)

class IContextManager(ABC):
    """
    抽象基类，定义上下文管理器的接口。
    """

    @abstractmethod
    def get_context(self, request: ContextRequest) -> Dict[str, Any]:
        """
        根据请求协调 Providers 生成并合并最终的上下文。

        Args:
            request (ContextRequest): 包含生成上下文所需信息的请求对象。

        Returns:
            Dict[str, Any]: 一个字典，包含所有合并后的上下文信息，
                            可以直接用于提示词模板渲染。
                            例如: {'project_name': 'MyProject', 'relevant_code': '...', ...}
        """
        pass

    # 可选：注册和管理 Providers
    # @abstractmethod
    # def register_provider(self, provider: 'IContextProvider') -> None:
    #     """
    #     注册一个上下文提供者。
    #     """
    #     pass

    # @abstractmethod
    # def unregister_provider(self, provider_name: str) -> None:
    #     """
    #     注销一个上下文提供者。
    #     """
    #     pass

    # 可选：基于管道配置的上下文获取 (用于高级场景)
    # @abstractmethod
    # def get_context_by_pipeline(self, request: ContextRequest, pipeline_config: 'ContextPipelineConfig') -> Dict[str, Any]:
    #     """
    #     根据指定的管道配置来获取上下文。
    #     """
    #     pass
