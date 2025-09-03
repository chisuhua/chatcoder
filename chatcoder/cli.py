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
from chatcoder.core.init import (init_project, validate_config)
from chatcoder.core.prompt import render_prompt
from chatcoder.core.context import generate_context_snapshot
from chatcoder.core.state import (
    load_task_state,
    save_task_state,
    generate_task_id,
    list_task_states,
    get_task_file_path
)



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
    click.echo("🔍 正在生成上下文快照...\n")

    try:
        snapshot = generate_context_snapshot()

        # 输出核心字段
        keys_to_show = [
            "project_name",
            "project_language",
            "project_type",
            "framework",
            "test_runner",
            "format_tool",
            "core_files",
            "context_snapshot"
        ]

        for key in keys_to_show:
            value = snapshot.get(key)
            if key == "context_snapshot":
                click.echo(value)  # Markdown 格式直接输出
            elif key == "core_files":
                if value:
                    click.echo(f"\n## 🔍 扫描到 {len(value)} 个核心文件")
                    for filepath in sorted(value.keys()):
                        info = value[filepath]
                        click.echo(f"  📄 {filepath} (hash:{info['hash']})")
            elif value:
                click.echo(f"🔹 {key}: {value}")

    except Exception as e:
        click.echo(click.style(f"❌ 生成上下文失败: {e}", fg="red"))
        raise click.Abort()


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
    #template_path = resolve_template_path(template)
    #if not Path(template_path).exists():
    #    error(f"模板不存在: {template_path}")
    #    return

    # 2. 加载前置任务（可选）
    previous_task = None
    if after and after != "none":
        previous_task = load_task_state(after)
        if not previous_task:
            error(f"前置任务不存在: {after}")
            return

        # ✅ 新增：检查任务状态是否可继承
        status = previous_task.get("status", "pending")
        if status != "confirmed":
            error(f"❌ 前序任务 {after} 状态为 '{status}'，必须是 'confirmed'")
            warning("提示：请先人工审核任务内容，或使用 state-confirm <task_id> 标记为确认")
            return

        success(f"✅ 使用已确认任务作为上下文: {after}")

    # 3. 生成当前任务 ID
    task_id = generate_task_id()
    info(f"当前任务 ID: {task_id}")

    try:
        # 4. 渲染提示词
        rendered = render_prompt(
            template_path=template,
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

@cli.command(name="state-confirm")
@click.argument("task_id")
def state_confirm(task_id):
    """标记任务为已确认"""
    task_file = get_task_file_path(task_id)
    if not task_file.exists():
        error(f"任务不存在: {task_id}")
        return

    try:
        with open(task_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 获取当前状态
        current_status = data.get("status", "pending")

        # 如果已经是 confirmed，提示用户
        if current_status == "confirmed":
            warning(f"⚠️  任务 {task_id} 已是 'confirmed' 状态，无需重复确认。")
            console.print_json(data=data)
            return

        # 更新状态
        data["status"] = "confirmed"
        data["confirmed_at"] = datetime.now().isoformat()
        data["confirmed_at_str"] = datetime.now().strfftime("%Y-%m-%d %H:%M:%S")

        with open(task_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        success(f"✅ 任务 {task_id} 已标记为 confirmed")

    except Exception as e:
        error(f"确认失败: {e}")


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


@cli.command(name="validate")
def config_validate():
    """验证 config.yaml 是否合法"""
    validate_config()

@cli.command()
def debug_context():
    """调试：打印当前上下文"""
    from chatcoder.core.context import debug_print_context
    debug_print_context()

# ------------------------------
# 主入口
# ------------------------------

if __name__ == '__main__':
    cli()
