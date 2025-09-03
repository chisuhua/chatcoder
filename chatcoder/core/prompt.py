# chatcoder/core/prompt.py
import os
from pathlib import Path
import jinja2
from typing import Dict, Any, Optional

from ..utils.console import console
from .context import generate_context_snapshot

# 📁 模板根目录（相对于当前文件）
PROJECT_ROOT= Path(__file__).parent.parent.parent
TEMPLATES_DIR = PROJECT_ROOT / "ai-prompts" / "."

def create_jinja_env() -> jinja2.Environment:
    """
    创建支持 include 的 Jinja2 环境
    支持从 ai-prompts/common/ 和 ai-prompts/workflows/ 中加载模板
    """
    loader = jinja2.FileSystemLoader(str(TEMPLATES_DIR))
    env = jinja2.Environment(
        loader=loader,
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    return env

def resolve_template_path(template: str) -> str:
    """解析模板路径：支持别名 + 自动补全"""
    ALIASES = {
        'context': 'common/context.md.j2',
        'feature': 'workflows/feature.md.j2',
        'analyze': 'workflows/step1-analyze.md.j2',
        'design': 'workflows/step2-design.md.j2',
        'implement': 'workflows/step3-implement.md.j2',
        'test': 'workflows/step4-test.md.j2',
        'summary': 'workflows/step5-summary.md.j2',
    }
    if template in ALIASES:
        template = ALIASES[template]

    # 自动补全 .j2 扩展名
    if not template.endswith(('.j2', '.md')):
        template += '.j2'
   
    #if not template.startswith("ai-prompts/"):
    #  template = f"ai-prompts/{template}"
    return template


def render_prompt(
    template_path: str,
    description: str,
    previous_task: Optional[Dict[str, Any]] = None,
    **kwargs
) -> str:

    resolved = resolve_template_path(template_path)
    print(f"🔍 [DEBUG] resolved = {resolved}")  # 👈 加这行
    template_file = TEMPLATES_DIR / resolved
    print(f"📁 [DEBUG] template_file = {template_file}")  # 👈 加这行
    print(f"📌 [DEBUG] TEMPLATES_DIR = {TEMPLATES_DIR}")  # 👈 加这行


    try:
        try:
            rel_path = Path(resolved).relative_to(TEMPLATES_DIR)
        except ValueError:
            raise ValueError(f"模板 {resolved} 必须在 {TEMPLATES_DIR} 目录下")
        # 使用统一的 Jinja2 环境（支持 include）
        env = create_jinja_env()
        template = env.get_template(str(rel_path))

        # 生成核心上下文
        context = generate_context_snapshot()
        context.update(kwargs)  # 合并额外参数
        
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
    """
    template_path = TEMPLATES_DIR / "workflows" / f"step-{step}.md"
    if not template_path.exists():
        available = [f.stem for f in (TEMPLATES_DIR / "workflows").glob("step-*.md")]
        raise FileNotFoundError(
            f"未找到模板: {template_path}\n"
            f"可用模板: {available}"
        )
    
    return template_path


# --- 便捷函数 ---
def render_analyze_prompt(description: str, previous_task: Optional[Dict[str, Any]] = None, **kwargs) -> str:
    path = get_template_path("analyze")
    return render_prompt(str(path), description, previous_task, **kwargs)

def render_design_prompt(description: str, previous_task: Optional[Dict[str, Any]] = None, **kwargs) -> str:
    path = get_template_path("design")
    return render_prompt(str(path), description, previous_task, **kwargs)

def render_implement_prompt(description: str, previous_task: Optional[Dict[str, Any]] = None, **kwargs) -> str:
    path = get_template_path("implement")
    return render_prompt(str(path), description, previous_task, **kwargs)

def render_test_prompt(description: str, previous_task: Optional[Dict[str, Any]] = None, **kwargs) -> str:
    path = get_template_path("test")
    return render_prompt(str(path), description, previous_task, **kwargs)

def render_summary_prompt(description: str, previous_task: Optional[Dict[str, Any]] = None, **kwargs) -> str:
    path = get_template_path("summary")
    return render_prompt(str(path), description, previous_task, **kwargs)


# --- 调试工具 ---

def debug_render(template_path: str, **kwargs):
    console.print(f"[bold]📄 模板路径:[/bold] {template_path}")
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()
        console.print(f"[bold]📝 模板内容:[/bold]\n{template_content}\n")
        rendered = render_prompt(template_path, "调试任务描述", **kwargs)
        console.print(f"[bold]✨ 渲染结果:[/bold]\n{rendered}")
    except Exception as e:
        console.print(f"[red]❌ 调试渲染失败: {e}[/red]")
