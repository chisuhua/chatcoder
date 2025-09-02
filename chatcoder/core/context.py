"""
上下文管理模块：负责初始化项目、解析上下文、生成快照
"""
from pathlib import Path
from typing import Dict, Any
import shutil
from chatcoder.utils import ensure_dir, read_template

# 内置模板目录（相对于包根）
AI_PROMPTS_DIR = Path(__file__).parent.parent / "templates" / "ai-prompts"


def init_project() -> None:
    """初始化项目：复制 ai-prompts/ 并生成 PROJECT_CONTEXT.md"""
    current_dir = Path.cwd()

    # 复制 ai-prompts/
    dst = current_dir / "ai-prompts"
    if dst.exists():
        print("⚠️  ai-prompts/ 已存在，跳过复制")
    else:
        try:
            shutil.copytree(AI_PROMPTS_DIR, dst)
            print("✅ ai-prompts/ 初始化完成")
        except Exception as e:
            raise RuntimeError(f"复制 ai-prompts/ 失败: {e}")

    # 生成 PROJECT_CONTEXT.md
    ctx_path = current_dir / "PROJECT_CONTEXT.md"
    if ctx_path.exists():
        print("⚠️  PROJECT_CONTEXT.md 已存在")
    else:
        try:
            template = read_template("ai-prompts/common/context-template.md")
            ctx_path.write_text(template, encoding="utf-8")
            print("✅ PROJECT_CONTEXT.md 生成完成")
        except Exception as e:
            raise RuntimeError(f"生成 PROJECT_CONTEXT.md 失败: {e}")

    print("\n📌 请编辑 PROJECT_CONTEXT.md 并填写项目信息")


def parse_context_file() -> Dict[str, str]:
    """
    解析 PROJECT_CONTEXT.md 为字典
    支持格式：- 键: 值  或  键: 值
    """
    ctx_path = Path("PROJECT_CONTEXT.md")
    if not ctx_path.exists():
        raise FileNotFoundError("PROJECT_CONTEXT.md 未找到，请先运行 chatcoder init")

    content = ctx_path.read_text(encoding="utf-8")
    result = {}

    lines = content.splitlines()
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#') or ':' not in line:
            continue

        # 移除列表符号 "- "
        if line.startswith('- '):
            line = line[2:]

        if ':' in line:
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip()
            if key:  # 避免空 key
                result[key] = value

    return result


def generate_context_snapshot() -> str:
    """
    生成用于 prompt 的上下文摘要（Markdown 格式）
    """
    try:
        ctx = parse_context_file()
        items = [f"- {k}: {v}" for k, v in ctx.items() if v.strip()]
        if not items:
            return "## 📂 项目上下文\n- 无可用上下文"
        return "## 📂 项目上下文\n" + "\n".join(items)
    except Exception as e:
        return f"## 📂 项目上下文\n- 解析失败: {e}"
