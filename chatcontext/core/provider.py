# chatcontext/core/provider.py
"""ContextProvider 抽象基类"""

from abc import ABC, abstractmethod
from typing import List
from .models import ContextRequest, ProvidedContext, ContextType

class IContextProvider(ABC):
    """上下文提供者接口"""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider 的唯一名称"""
        pass

    @abstractmethod
    def provide(self, request: ContextRequest) -> List[ProvidedContext]:
        """
        核心方法：根据请求生成并返回上下文片段。
        """
        pass

    # --- v1.1 可选扩展方法 (提供默认实现以保持向后兼容) ---
    def get_priority(self, request: ContextRequest) -> int:
        """
        (可选) 根据请求动态返回此 Provider 的优先级 (0-100)。
        用于排序，高优先级先调用。
        """
        return 50 # 默认优先级

    def can_provide(self, request: ContextRequest) -> bool:
        """
        (可选) 前置检查，判断此 Provider 是否应该参与本次上下文生成。
        """
        return True # 默认参与

    def get_supported_types(self) -> List[ContextType]:
        """
        (可选) 返回此 Provider 支持的上下文类型。
        """
        return [ContextType.INFORMATIONAL] # 默认

    def get_supported_project_types(self) -> List[str]:
        """
        (可选) 返回此 Provider 支持的项目类型。
        '*' 表示支持所有。
        """
        return ['*'] # 默认支持所有
