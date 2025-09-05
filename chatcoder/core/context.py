# chatcoder/core/context.py
"""
上下文管理模块：负责初始化项目、解析上下文、生成快照
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

PHASE_SPECIFIC_PATTERNS = {
    # 分析和设计阶段：关注项目结构、模型、接口定义、配置
    "analyze": ["**/models.py", "**/schemas.py", "**/interfaces.py", "**/types.py", "**/config.py", "**/settings.py"],
    "design": ["**/interfaces.py", "**/abstract*.py", "**/base*.py", "**/models.py", "**/schemas.py", "**/api/*.py"],
    # 实现阶段：关注工具函数、辅助类、核心业务逻辑、以及可能被修改的文件
    "implement": ["**/utils.py", "**/helpers.py", "**/common/*.py", "**/lib/*.py", "**/services/*.py", "**/core/*.py"],
    # 测试阶段：关注测试文件和被测试的实现
    "test": ["**/tests/**/*", "**/*test*.py", "**/test_*.py", "**/spec/**/*"],
    # 通用阶段或其他未指定阶段
    # "default": [...] # 可以定义，但下面的逻辑会回退到 CORE_PATTERNS
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


def generate_context_snapshot(phase: Optional[str] = None): # 新的
    """
    生成上下文快照，用于模板渲染。

    Args:
        phase (Optional[str]): 当前任务的阶段 (e.g., 'analyze', 'design', 'implement').
                               用于动态调整上下文内容。
    """
    # --- 修改点结束 ---
    try:
        ctx = parse_context_file()

        # === 1. 构建 Markdown 格式的上下文摘要（原有逻辑）===
        snapshot = "## 🧩 项目上下文\n"
        if ctx:
            # 过滤掉空值
            non_empty_ctx = {k: v for k, v in ctx.items() if v}
            if non_empty_ctx:
                snapshot += "\n".join(f"- {k}: {v}" for k, v in non_empty_ctx.items())
            else:
                snapshot += "- 无上下文信息"
        else:
            snapshot += "- 无上下文信息"

        project_type = detect_project_type()
        # print(f"[DEBUG] Detected project type: {project_type}") # 可选调试

        # 优先从 config.yaml 加载
        core_patterns = load_core_patterns_from_config()
        if not core_patterns:
            # print(f"[DEBUG] No core_patterns in config, using defaults for {project_type} and phase {phase}") # 可选调试

            # 如果 config 中没有定义，则根据 phase 和 project_type 动态选择
            if phase and phase in PHASE_SPECIFIC_PATTERNS:
                # 1. 首选：使用与当前 phase 相关的预定义模式
                core_patterns = PHASE_SPECIFIC_PATTERNS[phase]
                # print(f"[DEBUG] Using phase-specific patterns for '{phase}'") # 可选调试
            else:
                # 2. 回退：使用基于项目类型的通用模式
                core_patterns = CORE_PATTERNS.get(project_type, ["**/*.py"])
                # print(f"[DEBUG] Using project-type patterns for '{project_type}' or default") # 可选调试

        core_files = {}
        root_path = Path(".")
        for pattern in core_patterns:
            try:
                # print(f"[DEBUG] Searching for pattern: {pattern}") # 可选调试
                for file_path in root_path.glob(pattern):
                    # print(f"[DEBUG] Found file: {file_path}") # 可选调试
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
            except Exception as e:
                # 捕获单个 pattern 的错误，避免中断整个过程
                print(f"⚠️  处理模式 '{pattern}' 时出错: {e}")

        # 添加到快照展示
        if core_files:
            snapshot += f"\n\n## 🔍 核心文件 ({len(core_files)} 个)\n"
            # 按文件路径排序以保证一致性
            for fp in sorted(core_files.keys()):
                info = core_files[fp]
                snapshot += f"- `{fp}` (hash:{info['hash']})\n"
                if info.get("snippet") == " <empty> ":
                    snapshot += "  → (空文件)\n"
                else:
                    lines = info["snippet"].splitlines()[:4] # 限制显示行数
                    for line in lines:
                        snapshot += f"  {line}\n"
                    if len(info["snippet"].splitlines()) > 4:
                        snapshot += "  ...\n"

        # === 3. 构建最终结果：保留原有字段 + 新增核心文件信息 ===
        result = DEFAULT_CONTEXT.copy()
        result.update(ctx)  # 用户配置优先
        result["context_snapshot"] = snapshot
        result["project_type"] = project_type
        result["core_patterns"] = core_patterns # 可能有用，或用于调试
        result["core_files"] = core_files

        return result

    except Exception as e:
        # 安全降级：返回默认上下文
        print(f"⚠️ 生成上下文快照时出错: {e}") # 可选：记录到日志
        fallback = DEFAULT_CONTEXT.copy()
        fallback["context_snapshot"] = f"## 🧩 项目上下文\n- 加载失败: {str(e)}"
        fallback["project_type"] = "unknown"
        fallback["core_files"] = {}
        fallback["core_patterns"] = []
        return fallback


def _extract_code_snippet(content: str, suffix: str) -> str:
    """
    智能提取代码片段，按语言做语义化处理
    """
    content = content.strip()
    if not content:
        return " <empty> "
    lines = content.splitlines()

    # 根据后缀推断语言
    lang = _suffix_to_lang(suffix)

    # 截断最大行数
    MAX_LINES = 15

    # === 1. Python: 提取类、函数、import 和 main 入口 ===
    if lang == "python":
        # 保留 import
        imports = [line for line in lines if line.startswith(("import ", "from "))]

        # 找到前几个函数/类定义
        defs = []
        for i, line in enumerate(lines):
            if line.startswith(("def ", "class ")) and not line.rstrip().endswith(": pass"):
                block = _get_code_block(lines, i)
                defs.append(block)
                if len(defs) >= 2:
                    break

        # main 入口
        main_block = None
        for i, line in enumerate(lines):
            if line.strip().startswith("if __name__ ") and "__main__" in line:
                main_block = _get_code_block(lines, i)
                break

        parts = []
        if imports:
            # parts.append("...")  # 省略部分导入，保留最后几个
            parts.extend(imports[-3:])  # 最后 3 个重要导入
        if defs:
            parts.append("# Key Functions/Classes: ")
            parts.extend(defs)
        if main_block:
            parts.append("# Entry Point: ")
            parts.append(main_block)
        if not parts:
             # 如果没找到特定结构，返回前几行
             parts = lines[:5]

        snippet = "\n".join(parts[:MAX_LINES])
        return snippet + ("\n# ... (truncated)" if len(parts) > MAX_LINES else "")

    # === 2. C++: 提取 include, class, struct, function ===
    elif lang in ("cpp", "c"):
        includes = [line for line in lines if line.strip().startswith("#include")]
        classes_structs = []
        functions = []
        namespaces = []

        for i, line in enumerate(lines):
            stripped_line = line.strip()
            if stripped_line.startswith("class ") or stripped_line.startswith("struct "):
                # 简单提取类/结构体声明行
                classes_structs.append(stripped_line.split("{")[0].rstrip() + " {...};")
                if len(classes_structs) >= 2:
                     # 避免过多
                     classes_structs[-1] += " ..."
                     break
            elif stripped_line.startswith(("void ", "int ", "bool ", "std::", "template ")) and "(" in stripped_line and ");" in stripped_line:
                 # 简单匹配函数声明
                 functions.append(stripped_line)
                 if len(functions) >= 3:
                     functions[-1] += " ..."
                     break
            elif stripped_line.startswith("namespace "):
                namespaces.append(stripped_line.split("{")[0].rstrip() + " {...}")

        parts = []
        if includes:
            parts.extend(includes[:3]) # 前几个 include
        if namespaces:
             parts.append("// Namespaces: ")
             parts.extend(namespaces[:1])
        if classes_structs:
            parts.append("// Classes/Structs: ")
            parts.extend(classes_structs)
        if functions:
            parts.append("// Functions: ")
            parts.extend(functions)
        if not parts:
             # 默认返回前几行
             parts = lines[:5]

        snippet = "\n".join(parts[:MAX_LINES])
        return snippet + ("\n// ... (truncated)" if len(parts) > MAX_LINES else "")

    # === 3. 默认：取前几行 + 后几行 ===
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
    if start_idx >= len(lines):
        return ""

    block = [lines[start_idx].rstrip()] # 移除行尾换行符
    # 更稳健地处理缩进
    first_line_indent = len(lines[start_idx]) - len(lines[start_idx].lstrip())
    i = start_idx + 1

    while i < len(lines):
        line = lines[i]
        stripped_line = line.lstrip()
        if not stripped_line:
            block.append("") # 保留空行
            i += 1
            continue

        # 计算当前行的实际缩进（空格数）
        current_indent = len(line) - len(stripped_line)

        # 如果当前行缩进小于起始行缩进，并且不是空行或注释，则可能是块结束
        # （需要考虑非缩进语言如 C++ 的情况，这里主要适用于 Python）
        # 对于 Python，这是一个合理的判断
        if current_indent < first_line_indent and stripped_line not in ('#', '"""', "'''") and not stripped_line.startswith('#'):
             # 检查是否是同级或更高级别的定义开始
             if stripped_line.startswith(('def ', 'class ', 'if __name__')):
                 break # 停在下一个同级定义前

        block.append(line.rstrip()) # 移除行尾换行符
        i += 1
        if len(block) >= 20:  # 防止太长
            block.append("    # ... (truncated in snippet)")
            break

    return "\n".join(block)


# def _get_indent(line: str) -> int:
#     return len(line) - len(line.lstrip())


def _suffix_to_lang(suffix: str) -> Optional[str]:
    mapping = {
        ".py": "python",
        # ".js": "javascript",
        # ".ts": "typescript",
        # ".go": "go",
        # ".rs": "rust",
        ".cpp": "cpp",
        ".cc": "cpp",
        ".cxx": "cpp",
        ".c": "c",
        ".h": "cpp", # Header for C/C++
        ".hpp": "cpp",
        # ".java": "java",
        # ".rb": "ruby",
        # ".php": "php"
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


# ------------------------------
# 调试工具
# ------------------------------

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
