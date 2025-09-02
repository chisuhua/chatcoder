import os
from pathlib import Path
import jinja2
from typing import Dict, Any, Optional

from ..utils.console import console
from .context import generate_context_snapshot


def render_prompt(
    template_path: str,
    description: str,
    previous_task: Optional[Dict[str, Any]] = None,
    **kwargs
) -> str:
    template_file = Path(template_path)
    
    if not template_file.exists():
        raise FileNotFoundError(f"模板文件不存在: {template_path}")

    # 创建 Jinja2 环境
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(template_file.parent)),
        autoescape=False,  # 提示词无需 HTML 转义
        trim_blocks=True,   # 去除块后换行
        lstrip_blocks=True  # 去除块前空格
    )

    try:
        # 获取模板
        template = env.get_template(template_file.name)

        # 生成上下文：优先使用 generate_context_snapshot()
        context = generate_context_snapshot()
        
        # 合并用户传入的额外上下文
        context.update(kwargs)
        
        # 注入核心变量
        context.update({
            "description": description,
            "previous_task": previous_task,
        })

        # 渲染模板
        rendered = template.render(**context)
        
        return rendered.strip()

    except jinja2.TemplateNotFound as e:
        raise FileNotFoundError(f"模板未找到: {e.name}")
    except jinja2.TemplateError as e:
        console.print(f"[red]❌ 模板渲染失败: {e}[/red]")
        raise
    except Exception as e:
        console.print(f"[red]❌ 渲染提示词时发生未知错误: {e}[/red]")
        raise


def get_template_path(step: str) -> Path:
    """
    根据步骤名获取模板路径（约定式路径）

    Args:
        step: 步骤名称，如 'analyze', 'design', 'implement', 'test', 'summary'

    Returns:
        模板文件的 Path 对象
    """
    base_dir = Path(__file__).parent.parent
    template_path = base_dir / "ai-prompts" / "workflows" / f"step-{step}.md"
    
    if not template_path.exists():
        # 可选：提供默认模板或抛出更友好错误
        available = [f.stem for f in (base_dir / "ai-prompts" / "workflows").glob("step-*.md")]
        raise FileNotFoundError(
            f"未找到模板: {template_path}\n"
            f"可用模板: {available}"
        )
    
    return template_path


# --- 便捷函数 ---

def render_analyze_prompt(description: str, previous_task: Optional[Dict[str, Any]] = None, **kwargs) -> str:
    """快捷生成分析阶段提示词"""
    path = get_template_path("analyze")
    return render_prompt(str(path), description, previous_task, **kwargs)


def render_design_prompt(description: str, previous_task: Optional[Dict[str, Any]] = None, **kwargs) -> str:
    """快捷生成设计阶段提示词"""
    path = get_template_path("design")
    return render_prompt(str(path), description, previous_task, **kwargs)


def render_implement_prompt(description: str, previous_task: Optional[Dict[str, Any]] = None, **kwargs) -> str:
    """快捷生成实现阶段提示词"""
    path = get_template_path("implement")
    return render_prompt(str(path), description, previous_task, **kwargs)


def render_test_prompt(description: str, previous_task: Optional[Dict[str, Any]] = None, **kwargs) -> str:
    """快捷生成测试阶段提示词"""
    path = get_template_path("test")
    return render_prompt(str(path), description, previous_task, **kwargs)


def render_summary_prompt(description: str, previous_task: Optional[Dict[str, Any]] = None, **kwargs) -> str:
    """快捷生成总结阶段提示词"""
    path = get_template_path("summary")
    return render_prompt(str(path), description, previous_task, **kwargs)


# --- 调试工具 ---

def debug_render(template_path: str, **kwargs):
    """调试用：打印渲染前后的模板"""
    console.print(f"[bold]📄 模板路径:[/bold] {template_path}")
    
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()
        console.print(f"[bold]📝 模板内容:[/bold]\n{template_content}\n")
        
        rendered = render_prompt(template_path, "调试任务描述", **kwargs)
        console.print(f"[bold]✨ 渲染结果:[/bold]\n{rendered}")
        
    except Exception as e:
        console.print(f"[red]❌ 调试渲染失败: {e}[/red]")
