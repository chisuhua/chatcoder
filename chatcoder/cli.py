"""
ChatCoder CLI 入口
"""
from pathlib import Path
import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from chatcoder.core.context import generate_context_snapshot
from chatcoder.core.prompt import render_prompt
from chatcoder.core.state import (
    load_task_state,
    save_task_state,
    generate_task_id,
    list_task_states
)

console = Console()

# 模板别名映射
ALIASES = {
    'feature': 'workflows/feature.md',
    'analyze': 'workflows/step1-analyze.md',
    'design': 'workflows/step2-design.md',
    'implement': 'workflows/step3-implement.md',
    'test': 'workflows/step4-test.md',
    'summary': 'workflows/step5-summary.md',
}

def resolve_template_path(template: str) -> str:
    """解析模板路径"""
    if template in ALIASES:
        template = ALIASES[template]
    if not template.startswith("ai-prompts/"):
        template = f"ai-prompts/{template}"
    return template

@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """🤖 ChatCoder - AI-Native Development Assistant"""
    if ctx.invoked_subcommand is None:
        console.print(Panel("[bold green]ChatCoder v0.1.0[/bold green]\nAI 协作协议引擎", expand=False))
        console.print("\n使用 [cyan]chatcoder --help[/cyan] 查看命令")


@cli.command()
def init():
    """🔧 初始化项目：复制模板并生成上下文文件"""
    from chatcoder.core.context import init_project
    try:
        init_project()
    except Exception as e:
        console.print(f"[red]❌ 初始化失败: {e}[/red]")


@cli.command()
def context():
    """📚 解析并显示项目上下文"""
    from chatcoder.core.context import parse_context_file
    try:
        ctx = parse_context_file()
        table = Table(title="📊 项目上下文", show_header=True, header_style="bold magenta")
        table.add_column("键", style="cyan", no_wrap=True)
        table.add_column("值", style="magenta")

        for k, v in ctx.items():
            table.add_row(k, v)

        console.print(table)
    except Exception as e:
        console.print(f"[red]❌ 错误: {e}[/red]")


@cli.command()
@click.argument('template', type=click.Path())
@click.argument('description', required=False)
@click.option('--after', help="前置任务 ID")
@click.option('--output', '-o', type=click.Path(), help="输出到文件")
def prompt(template, description, after, output):
    """生成结构化 AI 提问"""
    # 解析模板路径
    template_path = resolve_template_path(template)

    # 依赖检查
    previous_task = None
    if after and after != "none":
        previous_task = load_task_state(after)
        if not previous_task:
            console.print(f"[red]❌ 前置任务不存在: {after}[/red]")
            return

    # 生成当前任务 ID
    task_id = generate_task_id()
    console.print(f"[blue]📝 当前任务 ID: {task_id}[/blue]")

    try:
        rendered = render_prompt(
            template_path,
            description=description or "",
            after=after,
            previous_task=previous_task
        )

        # 保存当前任务状态
        save_task_state(
            task_id=task_id,
            template=template_path,
            description=description or "",
            context=generate_context_snapshot()
        )

        if output:
            Path(output).write_text(rendered, encoding="utf-8")
            console.print(f"[green]✅ Prompt 已保存到: {output}[/green]")
        else:
            console.print(Panel(rendered, title=f"📋 Prompt: {task_id}", border_style="blue"))

    except Exception as e:
        console.print(f"[red]❌ 生成 Prompt 失败: {e}[/red]")

@cli.command()
@click.argument('id')
def confirm(id):
    """✅ 记录人工确认（待实现）"""
    confirm_dir = Path(".chatcoder") / "confirmations"
    confirm_dir.mkdir(exist_ok=True)
    console.print(f"[green]📝 已创建确认目录: {confirm_dir}[/green]")
    #console.print(f"请创建 .chatcoder/confirmations/{id}.md 并填写摘要")


@cli.command()
def status():
    """📊 查看当前协作状态（待实现）"""
    console.print("[yellow]💡 提示：该命令将在第4周实现[/yellow]")

@cli.command(name="state-ls")
def state_ls():
    """列出所有持久化任务状态"""
    tasks = list_task_states()
    if not tasks:
        console.print("[yellow]📭 无任务记录[/yellow]")
        return

    table = Table("ID", "Template", "Description", "Created At", title="📊 任务状态列表")
    for t in tasks:
        table.add_row(
            t["task_id"],
            t["template"].replace("ai-prompts/", ""),
            t["description"],
            t["created_at_str"]
        )
    console.print(table)


@cli.command(name="state-show")
@click.argument('task_id')
def state_show(task_id):
    """查看指定任务的完整状态"""
    data = load_task_state(task_id)
    if not data:
        console.print(f"[red]❌ 任务不存在: {task_id}[/red]")
        return
    console.print(Panel(
        json.dumps(data, indent=2, ensure_ascii=False),
        title=f"🔍 任务详情: {task_id}"
    ))
if __name__ == '__main__':
    cli()
