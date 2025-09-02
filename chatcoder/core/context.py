# chatcoder/core/context.py
"""
上下文管理模块：负责初始化项目、解析上下文、生成快照

提供：
- context.yaml 文件解析
- 上下文快照生成（用于模板渲染）
- 基础字段安全降级机制
"""
from pathlib import Path
import yaml
from typing import Dict, Any, Optional

# 全局常量
CONTEXT_FILE = Path(".chatcoder") / "context.yaml"
DEFAULT_CONTEXT = {
    "project_language": "unknown",
    "test_runner": "unknown",
    "format_tool": "unknown",
    "project_description": "未提供项目描述"
}


def parse_context_file() -> Dict[str, Any]:
    """
    解析 context.yaml 文件，返回字典。

    Returns:
        项目上下文字典

    Raises:
        FileNotFoundError: 若 context.yaml 不存在
        RuntimeError: 若 YAML 解析失败
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


def generate_context_snapshot() -> Dict[str, Any]:
    """
    生成上下文快照，用于模板渲染。

    将 context.yaml 中的所有键值对提升为 Jinja2 模板变量，
    并附加一个格式化的 context_snapshot 字段用于展示。

    Returns:
        包含上下文字段和格式化快照的字典
    """
    try:
        ctx = parse_context_file()

        # 构建 Markdown 格式的上下文摘要
        snapshot = "## 🧩 项目上下文\n"
        if ctx:
            snapshot += "\n".join(f"- {k}: {v}" for k, v in ctx.items() if v)
        else:
            snapshot += "- 无上下文信息"

        # 合并：所有原始字段 + 快照字段
        # 确保即使某些字段缺失，也有默认值
        result = DEFAULT_CONTEXT.copy()
        result.update(ctx)  # 用户配置优先
        result["context_snapshot"] = snapshot

        return result

    except Exception as e:
        # 安全降级：返回默认上下文
        fallback = DEFAULT_CONTEXT.copy()
        fallback["context_snapshot"] = f"## 🧩 项目上下文\n- 加载失败: {str(e)}"
        return fallback


# ------------------------------
# 附加功能（可选，用于 init.py）
# ------------------------------

def ensure_context_dir() -> Path:
    """
    确保 .chatcoder 目录存在，并返回路径。

    Returns:
        .chatcoder 目录路径
    """
    CONTEXT_FILE.parent.mkdir(parents=True, exist_ok=True)
    return CONTEXT_FILE.parent


def write_context_file(data: Dict[str, Any]) -> None:
    """
    将上下文字典写入 context.yaml 文件。

    Args:
        data: 要写入的字典

    Raises:
        IOError: 若写入失败
    """
    ensure_context_dir()
    try:
        with open(CONTEXT_FILE, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, allow_unicode=True, indent=2, sort_keys=False)
    except Exception as e:
        raise IOError(f"写入上下文文件失败: {e}")


def get_context_value(key: str, default: Any = None) -> Any:
    """
    安全获取上下文中的某个字段值。

    Args:
        key: 字段名
        default: 默认值

    Returns:
        字段值或默认值
    """
    try:
        ctx = parse_context_file()
        return ctx.get(key, default)
    except Exception:
        return default


# ------------------------------
# 调试工具
# ------------------------------

def debug_print_context() -> None:
    """
    调试用：打印当前上下文内容（命令行工具可调用）
    """
    try:
        ctx = parse_context_file()
        print("📄 当前上下文:")
        for k, v in ctx.items():
            print(f"  {k}: {v}")
    except Exception as e:
        print(f"❌ 无法加载上下文: {e}")
