# chatcoder/core/context.py
"""
上下文管理模块：负责解析和生成项目静态上下文 (精简版后备)
[注意] 此模块现在主要作为 chatcontext 库不可用时的极简后备方案。
核心的、动态的上下文生成功能已迁移至 chatcontext 库。
此版本专注于从传入的 config_data 和 context_data 生成静态上下文。
"""

from typing import Dict, Any, Optional, List
from .detector import detect_project_type # 如果探测逻辑仍需保留

# 默认上下文值
DEFAULT_CONTEXT = {
    "project_language": "unknown",
    "test_runner": "unknown",
    "format_tool": "unknown",
    "project_description": "未提供项目描述"
}

def generate_project_context_from_data(
    config_data: Optional[Dict[str, Any]],
    context_data: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    [精简后备] 根据传入的配置和上下文数据生成项目相关的静态上下文信息。
    [注意] 复杂的上下文生成功能已由 chatcontext 库提供。
    此函数仅作为 chatcontext 不可用时的极简后备。

    Args:
        config_data (Optional[Dict[str, Any]]): 从 config.yaml 加载的配置数据。
        context_data (Optional[Dict[str, Any]]): 从 context.yaml 加载的上下文数据。

    Returns:
        Dict[str, Any]: 包含项目静态信息的字典。
    """
    try:
        # 1. 初始化结果字典
        result = DEFAULT_CONTEXT.copy()

        # 2. 合并 context_data (用户在 context.yaml 中定义的)
        if context_data and isinstance(context_data, dict):
            # 过滤掉空值 (可选)
            non_empty_context_data = {k: v for k, v in context_data.items() if v is not None}
            result.update(non_empty_context_data) # context_data 优先级高于默认值

        # 3. 从 config_data 中提取特定信息 (如 core_patterns)
        core_patterns: Optional[List[str]] = None
        if config_data and isinstance(config_data, dict):
            cp = config_data.get("core_patterns")
            if isinstance(cp, list):
                core_patterns = cp
            # 可以从 config_data 中提取其他需要的静态信息

        # 4. (可选) 探测项目类型 (如果需要动态探测而非完全依赖配置)
        # detected_project_type = detect_project_type()
        # result["project_type"] = detected_project_type

        # 5. 添加从配置中提取的信息
        if core_patterns:
            result["core_patterns"] = core_patterns

        return result

    except Exception as e:
        # 安全降级：返回默认上下文
        print(f"⚠️ 从数据生成后备项目上下文时出错: {e}")
        fallback = DEFAULT_CONTEXT.copy()
        fallback["project_type"] = "unknown"
        return fallback

