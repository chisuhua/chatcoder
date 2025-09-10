# chatcoder/core/context.py
"""
上下文管理模块：负责初始化项目、解析上下文、生成快照 (简化版后备)
[注意] 此模块现在主要作为 chatcontext 库不可用时的极简后备方案。
核心的、动态的上下文生成功能已迁移至 chatcontext 库。
"""

from pathlib import Path
import hashlib
import yaml
from typing import Dict, Any, Optional, List
from .detector import detect_project_type
from .utils import read_file_safely

# 全局常量
CONTEXT_FILE = Path(".chatcoder") / "context.yaml"
CONFIG_FILE = Path(".chatcoder") / "config.yaml"
DEFAULT_CONTEXT = {
    "project_language": "unknown",
    "test_runner": "unknown",
    "format_tool": "unknown",
    "project_description": "未提供项目描述"
}

# --- 精简后备：保留一个非常基础的 CORE_PATTERNS ---
CORE_PATTERNS = {
    "python": ["**/*.py"],
    "python-django": ["**/models.py", "**/views.py", "**/apps.py"],
    "python-fastapi": ["**/main.py", "**/routers/*.py", "**/models/*.py"],
    "cpp": ["**/*.cpp", "**/*.h", "**/*.hpp", "**/*.cc"],
    "cpp-bazel": ["BUILD", "WORKSPACE", "**/*.cpp"],
    "unknown": []
}


def parse_context_file() -> Dict[str, Any]:
    """
    解析 context.yaml 文件，返回字典。
    """
    if not CONTEXT_FILE.exists():
        # 不抛出 FileNotFoundError，而是返回空字典或默认值，更宽容
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
            # 确保返回的是列表
            patterns = config.get("core_patterns")
            if isinstance(patterns, list):
                return patterns
            elif patterns is not None:
                 print(f"⚠️  {CONFIG_FILE} 中的 core_patterns 不是列表，已忽略。")
            return None
    except Exception as e:
        print(f"⚠️ 读取 {CONFIG_FILE} 失败: {e} ")
        return None


def generate_context_snapshot(phase: Optional[str] = None) -> Dict[str, Any]:
    """
    [Minimal Backward Compatibility] 生成极简的上下文快照。
    [注意] 复杂的上下文生成功能已由 chatcontext 库提供。
    此函数仅作为 chatcontext 不可用时的极简后备。
    """
    try:
        # 1. 加载用户定义的上下文
        user_context = parse_context_file()
        # 过滤掉空值
        non_empty_user_context = {k: v for k, v in user_context.items() if v}

        # 2. 探测项目类型
        project_type = detect_project_type()

        # 3. 构建极简的 Markdown 格式的上下文摘要
        snapshot_lines = ["## 🧩 项目上下文 (Fallback Mode)"]
        snapshot_lines.append("- ⚠️  Complex context generation is handled by the 'chatcontext' library.")
        snapshot_lines.append("- ℹ️  This is a minimal fallback snapshot.")
        snapshot_lines.append(f"- 📁 Project Type: {project_type}")
        
        if non_empty_user_context:
            snapshot_lines.append("\n### 📝 用户定义:")
            snapshot_lines.extend(f"- {k}: {v}" for k, v in non_empty_user_context.items())
        else:
            snapshot_lines.append("- 无用户定义上下文信息")

        # 4. (可选) 尝试加载非常基础的核心文件列表 (作为演示，非必需)
        #    这只是为了展示即使在后备模式下也能做一些事
        core_patterns = load_core_patterns_from_config()
        if not core_patterns:
            core_patterns = CORE_PATTERNS.get(project_type, ["**/*.py"])
        
        snapshot_lines.append(f"\n### 🔍 基础文件扫描 (Patterns: {', '.join(core_patterns[:3])}...):")
        root_path = Path(".")
        basic_file_count = 0
        core_files = {}
        for pattern in core_patterns[:2]: # 限制模式数量
            for file_path in root_path.glob(pattern):
                if not file_path.is_file():
                    continue
                content = read_file_safely(file_path)
                if not content:
                    continue
                basic_file_count += 1
                snapshot_lines.append(f"- 📄 {file_path}")
                file_hash = hashlib.md5(content.encode()).hexdigest()[:8]
                core_files[str(file_path)] = {
                     "hash": file_hash,
                     "snippet": content
                }


        if basic_file_count > 0:
             snapshot_lines.append(f"- ... (共找到 {basic_file_count} 个文件，已显示前 5 个)")

        snapshot = "\n".join(snapshot_lines)

        # 5. 构建最终结果
        result = DEFAULT_CONTEXT.copy()
        result.update(non_empty_user_context) # 用户配置优先
        result["context_snapshot"] = snapshot
        result["project_type"] = project_type
        # 明确不包含 chatcontext 生成的动态信息
        result["core_files"] = core_files
        #result["core_patterns"] = core_patterns

        return result

    except Exception as e:
        # 安全降级：返回默认上下文
        print(f"⚠️ 生成后备上下文快照时出错: {e}") # 可选：记录到日志
        fallback = DEFAULT_CONTEXT.copy()
        fallback["context_snapshot"] = (
            "## 🧩 项目上下文 (Fallback Mode)\n"
            "- ❌ 加载失败或发生错误\n"
            f"- 错误信息: {str(e)}\n"
            "- ⚠️  Complex context generation is handled by the 'chatcontext' library.\n"
            "- 请安装 chatcontext 以获取完整功能。"
        )
        fallback["project_type"] = "unknown"
        fallback["core_files"] = {}
        fallback["core_patterns"] = []
        return fallback


# --- 保留其他辅助函数和 CLI 调试函数 ---
def ensure_context_dir() -> Path:
    """
    确保 .chatcoder 目录存在，并返回路径。
    """
    CONTEXT_FILE.parent.mkdir(parents=True, exist_ok=True)
    return CONTEXT_FILE.parent


def write_context_file(data: Dict[str, Any]) -> None:
    """
    将上下文字典写入 context.yaml 文件。
    """
    ensure_context_dir()
    try:
        # 使用 sort_keys=False 保持用户定义的顺序
        with open(CONTEXT_FILE, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, allow_unicode=True, indent=2, sort_keys=False, default_flow_style=False)
    except Exception as e:
        raise IOError(f"写入上下文文件失败: {e}")


def get_context_value(key: str, default: Any = None) -> Any:
    """
    安全获取上下文中的某个字段值。
    """
    try:
        ctx = parse_context_file()
        return ctx.get(key, default)
    except Exception:
        return default


def debug_print_context() -> None:
    """
    调试用：打印当前上下文内容（命令行工具可调用）
    """
    try:
        ctx = parse_context_file()
        print("📄 当前上下文: ")
        if ctx:
            for k, v in ctx.items():
                print(f"  {k}: {v}")
        else:
            print("  (空)")
    except Exception as e:
        print(f"❌ 无法加载上下文: {e}")

