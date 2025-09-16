# chatcontext/providers/project_info.py
"""示例 Provider: 提供项目基本信息"""

from typing import List
from ..core.provider import IContextProvider
from ..core.models import ContextRequest, ProvidedContext, ContextType

class ProjectInfoProvider(IContextProvider):
    """提供项目类型、名称等基本信息"""

    @property
    def name(self) -> str:
        return "ProjectInfoProvider"

    def get_priority(self, request: ContextRequest) -> int:
        # 项目信息通常很重要，给高优先级
        return 90

    def get_supported_types(self) -> List[ContextType]:
        return [ContextType.GUIDING]

    # 假设项目信息对所有项目类型都适用
    # def get_supported_project_types(self): ... # 默认 ['*']

    def provide(self, request: ContextRequest) -> List[ProvidedContext]:
        content = {
            "project_type": request.project_type or "unknown",
            "project_name": request.project_name or "Unnamed Project",
            "project_language": request.project_language or "unknown",
            # 可以添加更多静态或探测到的信息
        }
        return [
            ProvidedContext(
                content=content,
                context_type=ContextType.GUIDING,
                provider_name=self.name,
                relevance_score=0.9, # 通常很相关
                summary="Basic project identification and type information."
            )
        ]
