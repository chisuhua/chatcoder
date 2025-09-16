# chatcontext/providers/core_files.py
"""示例 Provider: 提供核心文件内容"""

import os
from pathlib import Path
from typing import List
from ..core.provider import IContextProvider
from ..core.models import ContextRequest, ProvidedContext, ContextType

class CoreFilesProvider(IContextProvider):
    """提供项目核心文件的内容摘要"""

    @property
    def name(self) -> str:
        return "CoreFilesProvider"

    def get_supported_project_types(self) -> List[str]:
        # 仅为 Python 项目提供服务
        return ['python', 'python-django', 'python-fastapi']

    def can_provide(self, request: ContextRequest) -> bool:
        # 仅在特定阶段提供文件内容
        return request.current_phase in ['analyze', 'implement', 'test']

    def get_priority(self, request: ContextRequest) -> int:
        # 根据风险或阶段调整优先级
        if request.risk_level == 'high':
            return 85
        return 70

    def get_supported_types(self) -> List[ContextType]:
        return [ContextType.INFORMATIONAL]

    def provide(self, request: ContextRequest) -> List[ProvidedContext]:
        content = {}
        size_estimate = 0
        project_root = Path.cwd() # 或从 request/context 获取

        # 简单示例：读取 README 和主要配置文件
        key_files = ["README.md", "pyproject.toml", "requirements.txt"]
        for file_name in key_files:
            file_path = project_root / file_name
            if file_path.exists():
                try:
                    # 读取文件内容或生成摘要
                    file_content = file_path.read_text(encoding='utf-8')[:500] # 限制大小
                    content[f"file_{file_name.replace('.', '_')}"] = file_content
                    size_estimate += len(file_content)
                except Exception as e:
                    content[f"file_{file_name.replace('.', '_')}_error"] = str(e)

        return [
            ProvidedContext(
                content=content,
                context_type=ContextType.INFORMATIONAL,
                provider_name=self.name,
                relevance_score=0.7, # 中等相关性
                summary="Contents or summaries of key project files like README and config.",
                size_estimate=size_estimate
            )
        ]
