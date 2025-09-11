# chatcoder/core/context.py
"""
上下文管理模块：负责初始化项目、解析上下文 (精简版后备)
[注意] 此模块现在主要作为 chatcontext 库不可用时的极简后备方案。
核心的、动态的上下文生成功能已迁移至 chatcontext 库。
"""

from pathlib import Path
import yaml
from typing import Dict, Any, Optional, List
from .detector import detect_project_type

# 全局常量
CONTEXT_FILE = Path(".chatcoder") / "context.yaml"
CONFIG_FILE = Path(".chatcoder") / "config.yaml"
DEFAULT_CONTEXT = {
    "project_language": "unknown",
    "test_runner": "unknown",
    "format_tool": "unknown",
    "project_description": "未提供项目描述"
}

def parse_context_file() -> Dict[str, Any]:
    """
    解析 context.yaml 文件，返回字典。
    """
    if not CONTEXT_FILE.exists():
        raise FileNotFoundError(f"上下文文件不存在: {CONTEXT_FILE}")
    try:
        with open(CONTEXT_FILE, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            if data is None:
                return {}
            if not isinstance(data, dict):
                raise ValueError(f"上下文文件必须是 YAML 对象，实际为: {type(data)}")
            return data
    except yaml.YAMLError as e:
        raise RuntimeError(f"YAML 语法错误: {e}")
    except Exception as e:
        raise RuntimeError(f"解析上下文文件失败: {e}")

def load_core_patterns_from_config() -> Optional[List[str]]:
    """
    从 config.yaml 中加载 core_patterns 配置
    """
    if not CONFIG_FILE.exists():
        return None

    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            if not config:
                return None
            patterns = config.get("core_patterns")
            if isinstance(patterns, list):
                return patterns
            elif patterns is not None:
                 print(f"⚠️  {CONFIG_FILE} 中的 core_patterns 不是列表，已忽略。")
            return None
    except Exception as e:
        print(f"⚠️ 读取 {CONFIG_FILE} 失败: {e}")
        return None

def generate_project_context() -> Dict[str, Any]:
    """
    [精简后备] 生成项目相关的静态上下文信息。
    [注意] 复杂的上下文生成功能已由 chatcontext 库提供。
    此函数仅作为 chatcontext 不可用时的极简后备，主要读取静态配置。
    """
    try:
        # 1. 加载用户定义的上下文
        user_context = parse_context_file()
        # 过滤掉空值
        non_empty_user_context = {k: v for k, v in user_context.items() if v}

        # 2. 探测项目类型
        project_type = detect_project_type()

        # 3. 加载核心模式 (供 chatcontext 使用)
        core_patterns = load_core_patterns_from_config()

        # 4. 构建最终结果
        result = DEFAULT_CONTEXT.copy()
        result.update(non_empty_user_context) # 用户配置优先
        result["project_type"] = project_type
        if core_patterns:
            result["core_patterns"] = core_patterns

        return result

    except Exception as e:
        # 安全降级：返回默认上下文
        print(f"⚠️ 生成后备项目上下文时出错: {e}")
        fallback = DEFAULT_CONTEXT.copy()
        fallback["project_type"] = "unknown"
        return fallback

# --- 保留核心加载函数 ---
def ensure_context_dir() -> Path:
    """
    确保 .chatcoder 目录存在，并返回路径。
    """
    CONTEXT_FILE.parent.mkdir(parents=True, exist_ok=True)
    return CONTEXT_FILE.parent

# --- 移除或注释掉不再需要的函数 ---
# def write_context_file(...) -> None: ...
# def get_context_value(...) -> Any: ...
# def debug_print_context() -> None: ...
# def generate_context_snapshot(...) -> Dict[str, Any]: ... (已重命名为 generate_project_context)
