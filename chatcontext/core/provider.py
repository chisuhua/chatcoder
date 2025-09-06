# chatcontext/core/provider.py
"""
ChatContext 核心接口 - 上下文提供者 (IContextProvider)
定义了上下文提供者应提供的核心能力。
"""

from abc import ABC, abstractmethod
from typing import List
from .models import ContextRequest, ProvidedContext

class IContextProvider(ABC):
    """
    抽象基类，定义上下文提供者的接口。
    每个 Provider 负责生成特定类型或来源的上下文信息。
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        获取提供者的唯一名称。

        Returns:
            str: 提供者名称。
        """
        pass

    @abstractmethod
    def provide(self, request: ContextRequest) -> List[ProvidedContext]:
        """
        根据请求生成上下文。

        Args:
            request (ContextRequest): 包含生成上下文所需信息的请求对象。

        Returns:
            List[ProvidedContext]: 由该提供者生成的上下文列表。
                                   列表允许一个 Provider 返回多个片段或类型的上下文。
        """
        pass

    # 可选：定义提供者的能力或偏好
    # @abstractmethod
    # def get_supported_types(self) -> List[ContextType]:
    #     """
    #     获取该提供者支持的上下文类型。
    #
    #     Returns:
    #         List[ContextType]: 支持的类型列表。
    #     """
    #     pass

    # @abstractmethod
    # def get_priority(self) -> int:
    #     """
    #     获取该提供者的优先级（用于某些调度策略）。
    #
    #     Returns:
    #         int: 优先级数值。
    #     """
    #     pass
