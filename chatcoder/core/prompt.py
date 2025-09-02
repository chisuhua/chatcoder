"""
Prompt 生成模块：渲染模板 + 注入上下文
"""
from pathlib import Path
from typing import Dict, Any
from jinja2 import Template
from chatcoder.utils import read_template
from chatcoder.core.context import generate_context_snapshot


def render_prompt(template_name: str, description: str = "", **kwargs) -> str:
    """
    渲染 AI 提问模板

    Args:
        template_name: 模板路径，如 'python/feature-addition.md'
        description: 用户输入的功能描述
        **kwargs: 其他上下文变量

    Returns:
        渲染后的 Markdown 文本
    """
    try:
        # 1. 读取模板
        template_content = read_template(template_name)
        template = Template(template_content)

        # 2. 构建上下文
        context = {
            "description": description,
            "context_snapshot": generate_context_snapshot(),
            **kwargs
        }

        # 3. 渲染
        return template.render(**context)

    except FileNotFoundError:
        raise FileNotFoundError(f"模板未找到: {template_name}")
    except Exception as e:
        raise RuntimeError(f"渲染模板失败: {e}")
