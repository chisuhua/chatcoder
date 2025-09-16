# chatcontext/core/models.py
"""ChatContext 核心数据模型"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Union
from enum import Enum

class ContextType(Enum):
    """上下文信息的类型"""
    INFORMATIONAL = "informational"  # 通用信息
    GUIDING = "guiding"             # 指导性信息 (如项目结构、编码规范)
    ACTIONABLE = "actionable"       # 可操作信息 (如安全警告、待办事项)
    HISTORICAL = "historical"       # 历史交互记录

@dataclass
class ContextRequest:
    """
    向 ContextManager 发起上下文生成请求的数据结构。
    """
    # --- 与 ChatFlow/ChatCoder 关联的核心字段 ---
    workflow_instance_id: str # 对应 ChatCoder 传递的 instance_id
    feature_id: str           # 对应 ChatCoder 传递的 feature_id
    current_phase: str        # 对应 ChatCoder 传递的 phase_name
    task_description: str     # 对应 ChatCoder 传递的 task_description

    # --- 项目和环境信息 ---
    project_type: Optional[str] = None
    project_name: Optional[str] = None
    project_language: Optional[str] = None

    # --- 历史和用户输入 ---
    previous_outputs: Dict[str, Any] = field(default_factory=dict)
    user_inputs: Dict[str, Any] = field(default_factory=dict)

    # --- 请求约束和偏好 (v1.1) ---
    required_types: List[ContextType] = field(default_factory=list)
    automation_level: Optional[str] = None # e.g., 'low', 'medium', 'high'
    risk_level: Optional[str] = None       # e.g., 'low', 'medium', 'high'
    max_context_size: Optional[int] = None

    # --- 模式标志 ---
    is_preview: bool = False
    is_for_current_task: bool = False

@dataclass
class ProvidedContext:
    """
    单个 ContextProvider 提供的上下文片段。
    """
    content: Dict[str, Any]         # 实际的上下文内容
    context_type: ContextType       # 内容类型
    provider_name: str              # 提供此内容的 Provider 名称
    meta: Dict[str, Any] = field(default_factory=dict) # Provider 特定元数据

    # --- v1.1 增强字段 ---
    relevance_score: float = 1.0    # 相关性评分 (0.0 - 1.0)
    summary: Optional[str] = None   # 内容摘要
    size_estimate: Optional[int] = None # 大小估算 (字符数/token数)

@dataclass
class FinalContext:
    """
    ContextManager 最终合并、处理后返回的上下文。
    """
    merged_data: Dict[str, Any]  # 合并后的字典，供 Jinja2 渲染使用

    # --- 诊断和元信息 (v1.0/v1.1) ---
    provider_diagnostics: List[Dict[str, Any]] = field(default_factory=list)
    generation_time: float = 0.0  # 生成总耗时 (秒)
    total_size: int = 0           # 估算的总大小
    suggestions: List[str] = field(default_factory=list) # (v1.1) 增强建议

    # 可添加更多元数据，如使用的 Provider 列表等
