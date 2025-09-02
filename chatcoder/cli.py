# chatcoder/cli.py
"""
ChatCoder CLI 主入口（完整版：含状态管理）
"""
import click
import json
from pathlib import Path

from rich.panel import Panel

from chatcoder.utils.console import (
    console, info, success, warning, error,
    heading, show_welcome, confirm
)
from chatcoder.core.init import init_project
from chatcoder.core.prompt import render_prompt
from chatcoder.core.context import generate_context_snapshot
from chatcoder.core.state import (
    load_task_state,
    save_task_state,
    generate_task_id,
    list_task_states
)


# ------------------------------
# 模板别名映射（支持自动发现 + 别名）
# ------------------------------

def resolve_template_path(template: str) -> str:
    """解析模板路径：支持别名 + 自动补全"""
    ALIASES = {
        'feature': 'workflows/feature.md',
        'analyze': 'workflows/step1-analyze.md',
        'design': 'workflows/step2-design.md',
        'implement': 'workflows/step3-implement.md',
        'test': 'workflows/step4-test.md',
        'summary': 'workflows/step5-summary.md',
    }
    if template in ALIASES:
        template = ALIASES[template]
    if not template.startswith("ai-prompts/"):
        template = f"ai-prompts/{template}"
    return template


# ------------------------------
# CLI 主入口
# ------------------------------

@click.group(invoke_without_command=True)
@click.version_option("0.1.0", message="ChatCoder CLI v%(version)s")
@click.pass_context
def cli(ctx):
    """🤖 ChatCoder - AI-Native Development Assistant"""
    show_welcome()
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


# ------------------------------
# 命令 1: init
# ------------------------------

@cli.command()
def init():
    """🔧 初始化项目配置"""
    heading("项目初始化")
    state_dir = Path(".chatcoder")
    if state_dir.exists() and (state_dir / "context.yaml").exists():
        if not confirm("配置已存在，重新初始化将覆盖。继续？", default=False):
            info("已取消")
            return
    try:
        init_project()
        success("初始化完成！")
    except Exception as e:
        error(f"初始化失败: {e}")


# ------------------------------
# 命令 2: context
# ------------------------------

@cli.command()
def context():
    """📚 查看项目上下文"""
    from chatcoder.core.context import parse_context_file
    try:
        ctx = parse_context_file()
        console.print("[bold]📊 项目上下文:[/bold]")
        console.print_json(ctx)
    except Exception as e:
        error(f"读取失败: {e}")


# ------------------------------
# 命令 3: prompt（核心：含状态持久化）
# ------------------------------

@cli.command()
@click.argument('template', default='feature')  # 默认使用 feature 模板
@click.argument('description', required=False)
@click.option('--after', help="前置任务 ID")
@click.option('--output', '-o', type=click.Path(), help="输出到文件")
def prompt(template, description, after, output):
    """生成结构化 AI 提示词"""
    heading(f"生成提示词: {template}")

    # 1. 解析模板路径
    template_path = resolve_template_path(template)
    if not Path(template_path).exists():
        error(f"模板不存在: {template_path}")
        return

    # 2. 加载前置任务（可选）
    previous_task = None
    if after and after != "none":
        previous_task = load_task_state(after)
        if not previous_task:
            error(f"前置任务不存在: {after}")
            return

    # 3. 生成当前任务 ID
    task_id = generate_task_id()
    info(f"当前任务 ID: {task_id}")

    try:
        # 4. 渲染提示词
        rendered = render_prompt(
            template_path=template_path,
            description=description or "",
            previous_task=previous_task
        )

        # 5. 保存任务状态
        save_task_state(
            task_id=task_id,
            template=template_path,
            description=description or "",
            context=generate_context_snapshot()
        )

        # 6. 输出结果
        if output:
            Path(output).write_text(rendered, encoding="utf-8")
            success(f"提示词已保存: {output}")
        else:
            console.print(Panel(rendered, title=f"📋 Prompt: {task_id}", border_style="blue"))

    except Exception as e:
        error(f"生成失败: {e}")


# ------------------------------
# 命令 4: state-ls - 列出所有任务
# ------------------------------

@cli.command(name="state-ls")
def state_ls():
    """📋 列出所有持久化任务状态"""
    heading("任务状态列表")
    tasks = list_task_states()
    if not tasks:
        warning("无任务记录")
        return

    from rich.table import Table
    table = Table("ID", "Template", "Description", "Created At")
    for t in tasks:
        table.add_row(
            t["task_id"],
            t["template"].replace("ai-prompts/", ""),
            t["description"],
            t["created_at_str"]
        )
    console.print(table)


# ------------------------------
# 命令 5: state-show - 查看任务详情
# ------------------------------

@cli.command(name="state-show")
@click.argument('task_id')
def state_show(task_id):
    """🔍 查看指定任务的完整状态"""
    heading(f"任务详情: {task_id}")
    data = load_task_state(task_id)
    if not data:
        error(f"任务不存在: {task_id}")
        return
    console.print_json(data=data)


# ------------------------------
# 命令 6: confirm（占位）
# ------------------------------

#@cli.command()
#@click.argument('id')
#def confirm(id):
#    """✅ 记录人工确认（待实现）"""
#    confirm_dir = Path(".chatcoder") / "confirmations"
#    confirm_dir.mkdir(exist_ok=True)
#    success(f"已创建确认目录: {confirm_dir}")


# ------------------------------
# 命令 7: status（占位）
# ------------------------------

@cli.command()
def status():
    """📊 查看当前协作状态（待实现）"""
    warning("该命令将在后续版本实现")


# ------------------------------
# 主入口
# ------------------------------

if __name__ == '__main__':
    cli()
