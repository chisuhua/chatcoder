"""
ChatCoder CLI 入口
"""
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

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
@click.option('--output', '-o', type=click.Path(), help="输出到文件")
def prompt(template, description, output):
    """📨 生成结构化 AI 提问（Markdown）"""
    from chatcoder.core.prompt import render_prompt

    # 支持相对路径：python/feature-addition.md → ai-prompts/python/feature-addition.md
    if not template.startswith("ai-prompts/"):
        template = f"ai-prompts/{template}"

    try:
        rendered = render_prompt(template, description=description or "")

        if output:
            Path(output).write_text(rendered, encoding="utf-8")
            console.print(f"[green]✅ Prompt 已保存到: {output}[/green]")
        else:
            console.print(Panel(rendered, title="📋 AI Prompt", border_style="blue"))

    except Exception as e:
        console.print(f"[red]❌ 生成 Prompt 失败: {e}[/red]")


@cli.command()
@click.argument('id')
def confirm(id):
    """✅ 记录人工确认（待实现）"""
    console.print(f"[yellow]💡 提示：该命令将在第3周实现[/yellow]")
    console.print(f"请创建 .chatcoder/confirmations/{id}.md 并填写摘要")


@cli.command()
def status():
    """📊 查看当前协作状态（待实现）"""
    console.print("[yellow]💡 提示：该命令将在第4周实现[/yellow]")


if __name__ == '__main__':
    cli()
