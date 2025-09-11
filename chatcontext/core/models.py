# chatcontext/core/models.py
"""
ChatContext 核心数据模型
定义了在上下文提供、管理和请求过程中使用的核心数据结构。
"""

from enum import Enum
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

# --- 上下文类型分类 ---
class ContextType(Enum):
    """
    定义上下文的类型，帮助区分和管理不同来源或用途的上下文信息。
    """
    GUIDING = "guiding"       # 指导性上下文 (如系统提示词、任务目标)
    INFORMATIONAL = "informational" # 信息性上下文 (如项目代码、文档、知识库)
    ACTIONABLE = "actionable"   # 行动性上下文 (如历史输出、待执行指令)

# --- 上下文请求 ---
@dataclass
class ContextRequest:
    """
    描述生成上下文所需的信息请求。
    这是 ContextProvider 和 ContextManager 之间的主要通信载体。
    """
    # 核心标识与信息
    workflow_instance_id: str
    phase_name: str
    task_description: str

    project_type: Optional[str] = None
    project_name: Optional[str] = None
    project_language: Optional[str] = None

    # 上下文依赖
    previous_outputs: Dict[str, Any] = field(default_factory=dict) # 来自前序阶段/任务的输出
    user_inputs: Dict[str, Any] = field(default_factory=dict)      # 用户显式提供的信息

    # --- 调试/预览标志 ---
    is_preview: bool = False       # 是否为预览模式
    is_for_current_task: bool = False # 是否为当前活动任务生成上下文

    # 要求
    required_types: List[ContextType] = field(default_factory=list) # 请求的上下文类型
    # 可以扩展：例如，指定需要哪些特定文件的上下文，或者上下文的详细程度等

# --- 提供的上下文 ---
@dataclass
class ProvidedContext:
    """
    由单个 ContextProvider 生成的上下文内容。
    """
    content: Dict[str, Any] # 提供的具体上下文数据 (例如, {'project_info': '...', 'relevant_files': '...'})
    context_type: ContextType # 该上下文的类型
    provider_name: str        # 提供此上下文的 Provider 名称 (用于调试/元数据)
    metadata: Dict[str, Any] = field(default_factory=dict) # 额外的元数据 (例如, 生成时间, 来源详情)

# --- (未来) 上下文管道配置 (可选，用于高级场景) ---
# @dataclass
# class ContextPipelineConfig:
#     """
#     定义一个上下文生成管道的配置。
#     """
#     name: str
#     providers: List[str] # Provider 名称列表，定义执行顺序或优先级
#     merge_strategy: str  # 合并策略 (例如, 'merge_dicts', 'concatenate_markdown')
#     # 其他配置项...
