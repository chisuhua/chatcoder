# chatcoder/core/context.py
"""
上下文管理模块：负责初始化项目、解析上下文、生成快照
"""
from pathlib import Path
import hashlib
import yaml
from typing import Dict, Any, Optional
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

def load_core_patterns_from_config() -> Optional[list]:
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
            return config.get("core_patterns")
    except Exception as e:
        print(f"⚠️ 读取 {CONFIG_FILE} 失败: {e}")
        return None

def generate_context_snapshot() -> Dict[str, Any]:
    """
    生成上下文快照，用于模板渲染。
    """
    try:
        ctx = parse_context_file()

        # === 1. 构建 Markdown 格式的上下文摘要（原有逻辑）===
        snapshot = "## 🧩 项目上下文\n"
        if ctx:
            snapshot += "\n".join(f"- {k}: {v}" for k, v in ctx.items() if v)
        else:
            snapshot += "- 无上下文信息"

        # === 2. 智能识别项目类型并扫描核心文件 ===
        project_type = detect_project_type()

        # 优先从 config.yaml 加载
        core_patterns = load_core_patterns_from_config()
        if not core_patterns:
            core_patterns = CORE_PATTERNS.get(project_type, ["**/*.py"])

        core_files = {}
        for pattern in core_patterns:
            for file_path in Path(".").glob(pattern):
                if not file_path.is_file():
                    continue
                content = read_file_safely(file_path)
                if not content:
                    continue
                # 计算哈希
                file_hash = hashlib.md5(content.encode()).hexdigest()[:8]
                # 提取关键片段
                snippet = _extract_code_snippet(content, file_path.suffix)
                core_files[str(file_path)] = {
                    "hash": file_hash,
                    "snippet": snippet
                }

        # 添加到快照展示
        if core_files:
            snapshot += f"\n\n## 🔍 核心文件 ({len(core_files)} 个)\n"
            for fp in sorted(core_files.keys()):
                info = core_files[fp]
                snapshot += f"- `{fp}`\n"
                if info.get("snippet") == "<empty>":
                    snapshot += "  → (空文件)\n"
                else:
                    lines = info["snippet"].splitlines()[:4]
                    for line in lines:
                        snapshot += f"  {line}\n"
                    if len(info["snippet"].splitlines()) > 4:
                        snapshot += "  ...\n"


        # === 3. 构建最终结果：保留原有字段 + 新增核心文件信息 ===
        result = DEFAULT_CONTEXT.copy()
        result.update(ctx)  # 用户配置优先
        result["context_snapshot"] = snapshot
        result["project_type"] = project_type
        result["core_patterns"] = core_patterns
        result["core_files"] = core_files

        return result

    except Exception as e:
        # 安全降级：返回默认上下文
        fallback = DEFAULT_CONTEXT.copy()
        fallback["context_snapshot"] = f"## 🧩 项目上下文\n- 加载失败: {str(e)}"
        fallback["project_type"] = "unknown"
        fallback["core_files"] = {}
        fallback["core_patterns"] = []
        return fallback

#def _extract_code_snippet(content: str, suffix: str) -> str:
#   """
#   从文件内容中提取关键代码片段（前10行关键代码）
#   """
#   lines = content.splitlines()[:30]
#   key_lines = []

#   for line in lines:
#       line = line.strip()
#       if not line or line.startswith("#") or line.startswith("//"):
#           continue

#       if suffix == ".py":
#           if any(line.startswith(kw) for kw in ("def ", "class ", "import ", "from ")):
#               key_lines.append(line)
#       elif suffix in [".h", ".hpp", ".cpp", ".cc"]:
#           if any(kw in line for kw in ["class ", "struct ", "void ", "int ", "#include"]):
#               key_lines.append(line)

#   return "\n".join(key_lines[:10])

def _extract_code_snippet(content: str, suffix: str) -> str:
    """
    智能提取代码片段，按语言做语义化处理
    """
    content = content.strip()
    lines = content.splitlines()

    # 根据后缀推断语言
    lang = _suffix_to_lang(suffix)

    # 截断最大行数
    MAX_LINES = 15

    # === 1. Python: 提取类、函数、import 和 main 入口 ===
    if lang == "python":
        # 保留 import
        imports = [line for line in lines if line.startswith(("import", "from "))]

        # 找到前几个函数/类定义
        defs = []
        for i, line in enumerate(lines):
            if line.startswith(("def ", "class ")) and not line.endswith(": pass"):
                block = _get_code_block(lines, i)
                defs.append(block)
                if len(defs) >= 2:
                    break

        # main 入口
        main_block = None
        for i, line in enumerate(lines):
            if line.strip().startswith("if __name__") and "__main__" in line:
                main_block = _get_code_block(lines, i)
                break

        parts = []
        if imports:
            parts.append("...")  # 省略部分导入
            parts.extend(imports[-3:])  # 最后 3 个重要导入
        if defs:
            parts.append("# Key Functions/Classes:")
            parts.extend(defs)
        if main_block:
            parts.append("# Entry Point:")
            parts.append(main_block)

        return "\n".join(parts[:MAX_LINES]) + "\n..."

    # === 2. JavaScript/TypeScript ===
    elif lang in ("javascript", "typescript"):
        # 提取 export function / class / const App =
        exports = [line for line in lines if "export" in line and ("function" in line or "class" in line)]
        react_components = [line for line in lines if "const " in line and "= (" in line and "=>" in line]

        parts = []
        if exports:
            parts.append("// Exported Functions/Classes:")
            parts.extend(exports[:2])
        if react_components:
            parts.append("// React Components:")
            parts.extend(react_components[:1])
        if not parts:
            parts = lines[:5]

        return "\n".join(parts[:MAX_LINES]) + "\n..."

    # === 3. Go ===
    elif lang == "go":
        package_line = lines[0] if lines and lines[0].startswith("package ") else "package main"
        imports = [line for line in lines if "import" in line]
        funcs = [i for i, line in enumerate(lines) if line.startswith("func ")]

        parts = [package_line]
        if imports:
            parts.extend(imports[:3])
        for i in funcs[:2]:
            parts.extend(_get_code_block(lines, i))

        return "\n".join(parts[:MAX_LINES]) + "\n..."

    # === 4. 默认：取前几行 + 后几行 ===
    else:
        if len(lines) <= MAX_LINES:
            return content
        else:
            head = "\n".join(lines[:5])
            tail = "\n".join(lines[-(MAX_LINES-5):])
            return f"{head}\n...\n{tail}"


def _get_code_block(lines: list, start_idx: int) -> str:
    """
    提取一个函数或类定义的完整块（含嵌套）
    """
    block = [lines[start_idx]]
    indent = _get_indent(lines[start_idx])
    i = start_idx + 1

    while i < len(lines):
        if not lines[i].strip():
            block.append("")  # 保留空行
            i += 1
            continue
        current_indent = _get_indent(lines[i])
        if current_indent < indent and lines[i].strip() not in ["#", ""]:
            break
        block.append(lines[i])
        i += 1
        if len(block) >= 10:  # 防止太长
            block.append("    # ...")
            break

    return "\n".join(block)


def _get_indent(line: str) -> int:
    return len(line) - len(line.lstrip())


def _suffix_to_lang(suffix: str) -> Optional[str]:
    mapping = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".go": "go",
        ".rs": "rust",
        ".cpp": "cpp",
        ".c": "c",
        ".java": "java",
        ".rb": "ruby",
        ".php": "php"
    }
    return mapping.get(suffix.lower())
# ------------------------------
# 附加功能（可选，用于 init.py）
# ------------------------------

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
        with open(CONTEXT_FILE, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, allow_unicode=True, indent=2, sort_keys=False)
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
