# chatcoder/core/prompt.py
import os
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import jinja2

from ..utils.console import console
from .context import generate_context_snapshot

# 📁 模板根目录（相对于当前文件）
PROJECT_ROOT= Path(__file__).parent.parent.parent
TEMPLATES_DIR = PROJECT_ROOT / "ai-prompts" 
ALIASES = {
    'context': 'common/context.md.j2',
    'feature': 'workflows/feature.md.j2',
    'analyze': 'workflows/step1-analyze.md.j2',
    'design': 'workflows/step2-design.md.j2',
    'implement': 'workflows/step3-implement.md.j2',
    'test': 'workflows/step4-test.md.j2',
    'summary': 'workflows/step5-summary.md.j2',
}

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
    if template in ALIASES:
        template = ALIASES[template]

    # 自动补全 .j2 扩展名
    if not template.endswith(('.j2', '.md')):
        template += '.j2'
   
    #if not template.startswith("ai-prompts/"):
    #  template = f"ai-prompts/{template}"
    return template

def get_template_path(step: str) -> Path:
    """
    根据步骤名获取模板路径（约定式路径）
    """
    template_path = TEMPLATES_DIR / "workflows" / f"step-{step}.md.j2"
    if not template_path.exists():
        available = [f.stem for f in (TEMPLATES_DIR / "workflows").glob("step-*.md.j2")]
        raise FileNotFoundError(
            f"未找到模板: {template_path}\n"
            f"可用模板: {available}"
        )
    return template_path


def list_available_templates() -> List[Tuple[str, str, bool]]:
    """
    扫描 ai-prompts 目录，列出所有可用模板
    """
    templates = []

    # 1. 添加别名映射
    from .prompt import ALIASES  # 避免循环导入，可直接复制或重构
    for alias, path in ALIASES.items():
        template_file = TEMPLATES_DIR / path
        exists = template_file.exists()
        templates.append((alias, path, exists))

    # 2. 扫描 common/ 和 workflows/ 目录下的所有 .j2 文件
    search_dirs = ["common", "workflows"]
    for dname in search_dirs:
        search_path = TEMPLATES_DIR / dname
        if not search_path.exists():
            continue
        for file in search_path.rglob("*.j2"):
            rel_path = file.relative_to(TEMPLATES_DIR)
            path_str = str(rel_path).replace("\\", "/")
            # 避免重复
            if path_str not in [t[1] for t in templates]:
                templates.append(("(direct)", path_str, True))

    return sorted(templates, key=lambda x: (x[0], x[1]))

def render_prompt(
    template: str,
    description: str,
    previous_task: Optional[Dict[str, Any]] = None,
    **kwargs
) -> str:

    resolved = resolve_template_path(template)
    print(f"🔍 [DEBUG] resolved = {resolved}")  # 👈 加这行
    template_file = TEMPLATES_DIR / resolved
    print(f"📁 [DEBUG] template_file = {template_file}")  # 👈 加这行
    print(f"📌 [DEBUG] TEMPLATES_DIR = {TEMPLATES_DIR}")  # 👈 加这行

    if not template_file.exists():
        raise FileNotFoundError(f"模板文件不存在: {template_file}")

    try:
        abs_template = os.path.abspath(template_file)  # 规范化
        abs_templates = os.path.abspath(TEMPLATES_DIR)  # 规范化

        print(f"🔍 abs_template = {abs_template}")
        print(f"🔍 abs_templates = {abs_templates}")

        # ✅ 计算相对于模板目录的路径
        rel_path = os.path.relpath(abs_template, abs_templates)
        print(f"✅ [SUCCESS] rel_path = {rel_path}")  # 应该是 workflows/step1-analyze.md.j2
        # ✅ 确保路径分隔符是 /（Jinja2 要求）
        rel_path_forward = rel_path.replace("\\", "/")

        # 使用统一的 Jinja2 环境（支持 include）
        env = create_jinja_env()
        jinja_template = env.get_template(rel_path_forward)

        # 生成核心上下文
        context = generate_context_snapshot()
        context.update(kwargs)  # 合并额外参数
        
        # 注入核心变量
        context.update({
            "description": description,
            "previous_task": previous_task,
        })

        # 渲染模板
        rendered = jinja_template.render(**context)
        return rendered.strip()

    except jinja2.TemplateNotFound as e:
        raise FileNotFoundError(f"模板未找到: {e.name}")
    except jinja2.TemplateError as e:
        console.print(f"[red]❌ 模板渲染失败: {e}[/red]")
        raise
    except Exception as e:
        console.print(f"[red]❌ 渲染提示词时发生未知错误: {e}[/red]")
        raise



# --- 便捷函数 ---
def render_analyze_prompt(description: str, previous_task: Optional[Dict[str, Any]] = None, **kwargs) -> str:
    return render_prompt("analyze", description, previous_task, **kwargs)

def render_design_prompt(description: str, previous_task: Optional[Dict[str, Any]] = None, **kwargs) -> str:
    return render_prompt("design", description, previous_task, **kwargs)

def render_implement_prompt(description: str, previous_task: Optional[Dict[str, Any]] = None, **kwargs) -> str:
    return render_prompt("implement", description, previous_task, **kwargs)

def render_test_prompt(description: str, previous_task: Optional[Dict[str, Any]] = None, **kwargs) -> str:
    return render_prompt("test", description, previous_task, **kwargs)

def render_summary_prompt(description: str, previous_task: Optional[Dict[str, Any]] = None, **kwargs) -> str:
    return render_prompt("summary", description, previous_task, **kwargs)


# --- 调试工具 ---
def debug_render(template: str, **extra_context):
    """
    调试渲染：显示模板内容、解析路径、上下文、渲染结果
    """
    console.print(f"\n[bold blue]🔍 调试模板: {template}[/bold blue]")
    console.print(f"[dim]正在解析模板标识...[/dim]")

    try:
        # 1. 解析路径
        resolved = resolve_template_path(template)
        console.print(f"✅ 解析为: [cyan]{resolved}[/cyan]")

        template_file = TEMPLATES_DIR / resolved
        if not template_file.exists():
            console.print(f"[red]❌ 文件不存在: {template_file}[/red]")
            return

        # 2. 读取模板内容
        content = template_file.read_text(encoding="utf-8")
        console.print(f"\n[bold]📄 模板内容:[/bold]")
        console.print("[dim]" + "-"*60 + "[/dim]")
        console.print(content)
        console.print("[dim]" + "-"*60 + "[/dim]")

        # 3. 生成上下文快照
        context = generate_context_snapshot()
        context.update(extra_context)
        context.update({
            "description": "这是一条调试任务描述",
            "previous_task": {
                "task_id": "task_debug_123",
                "template": "analyze",
                "description": "上一个调试任务",
            } if extra_context.get("has_previous", True) else None
        })

        console.print(f"\n[bold]🧠 渲染上下文:[/bold]")
        for k, v in context.items():
            if isinstance(v, str) and len(v) > 100:
                console.print(f"  {k}: [dim]{v[:100]}...[/dim]")
            else:
                console.print(f"  {k}: {v}")

        # 4. 渲染
        console.print(f"\n[bold]✨ 正在渲染...[/bold]")
        rendered = render_prompt(template, context["description"], context["previous_task"])
        console.print(f"\n[bold green]✅ 渲染成功！结果:[/bold green]")
        console.print("[bold]" + "="*60 + "[/bold]")
        console.print(rendered)
        console.print("[bold]" + "="*60 + "[/bold]")

    except Exception as e:
        console.print(f"[red]❌ 调试失败: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
