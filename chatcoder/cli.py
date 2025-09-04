# chatcoder/cli.py
"""
ChatCoder CLI 主入口（完整版：含状态管理）
"""
import click
import json
from pathlib import Path

from rich.panel import Panel
from rich.table import Table

from chatcoder.utils.console import (
    console, info, success, warning, error,
    heading, show_welcome, confirm
)
from chatcoder.core.init import (init_project, validate_config)
from chatcoder.core.prompt import render_prompt, list_available_templates, debug_render
from chatcoder.core.context import generate_context_snapshot
from chatcoder.core.workflow import (
    get_workflow_path, load_workflow_schema, get_phase_order, get_feature_status
)
from chatcoder.core.state import (
    load_task_state,
    save_task_state,
    generate_feature_id,
    generate_task_id,
    list_task_states,
    get_tasks_dir,
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
# 创建 prompt 子命令组
prompt_group = click.Group(help="AI 提示词相关命令")

# 主命令行接口
#cli = click.Group()
cli.add_command(prompt_group, "prompt")


@prompt_group.command("prompt")
@click.argument('template', default='feature')  # 默认使用 feature 模板
@click.argument('description', required=False)
@click.option('--after', help="前置任务 ID")
@click.option('--output', '-o', type=click.Path(), help="输出到文件")
@click.option('--feature', help="指定 feature_id")
@click.option('--phase', type=click.Choice(['analyze', 'design', 'implement', 'test', 'summary']), help="开发阶段")
def prompt_cmd(template, description, after, output, feature, phase):
    """生成结构化 AI 提示词"""
    heading(f"生成提示词: {template}")

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
            template=template,
            description=description or "",
            previous_task=previous_task
        )

        # 5. 保存任务状态
        save_task_state(
            task_id=task_id,
            feature_id=feature,
            phase=phase or template,  # 默认用模板名作为 phase
            template=template,
            description=description or "",
            context={"rendered": rendered}
        )

        # 6. 输出结果
        if output:
            Path(output).write_text(rendered, encoding="utf-8")
            success(f"提示词已保存: {output}")
        else:
            console.print(Panel(rendered, title=f"📋 Prompt: {task_id}", border_style="blue"))

    except Exception as e:
        error(f"生成失败: {e}")


@prompt_group.command("list")
def list_templates():
    """列出所有可用模板"""
    heading("📋 可用模板列表")

    templates = list_available_templates()

    table = Table(
        "别名",
        "路径",
        "状态",
        title="模板清单"
    )

    for alias, path, exists in templates:
        status = "✅ 存在" if exists else "❌ 不存在"
        alias_styled = f"[bold]{alias}[/bold]" if alias != "(direct)" else alias
        table.add_row(alias_styled, path, status)

    console.print(table)

    total = len([t for t in templates if t[2]])
    console.print(f"\n[green]✔ 扫描完成，共找到 {total} 个有效模板[/green]")

@prompt_group.command("debug")
@click.argument('template')
@click.option('--desc', default="task", help='task name')
@click.option('--no-previous', is_flag=True, help='不使用前置任务上下文')
def debug_template(template, desc, no_previous):
    """调试指定模板的渲染过程"""
    extra_context = {"description": desc}
    if no_previous:
        extra_context["has_previous"] = False

    debug_render(template, **extra_context)

@prompt_group.command("edit")
@click.argument("template")
def edit_template(template: str):
    """
    用默认编辑器打开模板文件
    示例: chatcoder prompt edit analyze
    """
    from chatcoder.core.prompt import resolve_template_path

    # 解析模板路径
    rel_path = resolve_template_path(template)
    template_file = Path(__file__).parent.parent / "ai-prompts" / rel_path

    if not template_file.exists():
        error(f"模板文件不存在: {template_file}")
        # 提示用户是否创建
        if click.confirm("是否创建该文件？"):
            template_file.parent.mkdir(parents=True, exist_ok=True)
            template_file.write_text(
                f"<!-- {rel_path} - 模板内容 -->\n"
                f"<!-- 描述: {{{{ description }}}} -->\n\n"
                f"请在此输入模板内容...\n",
                encoding="utf-8"
            )
            success(f"✅ 已创建: {template_file}")
        else:
            return

    success(f"📄 正在打开: {template_file}")
    success(f"📍 路径: {rel_path}")

    # 尝试用系统默认编辑器打开
    try:
        import os
        import sys;
        from os import subprocess;
        if sys.platform == "win32":
            os.startfile(template_file)
        elif sys.platform == "darwin":
            subprocess.run(["open", template_file], check=True)
        else:  # Linux
            subprocess.run(["xdg-open", template_file], check=True)
    except Exception as e:
        warning(f"⚠️ 打开失败: {e}")
        console.print(f"你可以手动编辑: [cyan]{template_file}[/cyan]")

@prompt_group.command("preview")
@click.argument("template")
@click.argument("description", required=False)
@click.option("--after", help="前置任务 ID（用于上下文）")
def preview_template(template: str, description: str, after: str):
    """
    快速预览模板渲染结果（不保存任务状态）
    示例: chatcoder prompt preview analyze "用户可以发布文章"
    """
    heading(f"🖼️  预览模板: {template}")

    from chatcoder.core.prompt import render_prompt
    from chatcoder.core.state import load_task_state

    # 加载前置任务（可选）
    previous_task = None
    if after and after != "none":
        previous_task = load_task_state(after)
        if not previous_task:
            error(f"前置任务不存在: {after}")
            return
        success(f"✅ 使用上下文: {after}")

    try:
        rendered = render_prompt(
            template=template,
            description=description or "这是一条预览任务描述",
            previous_task=previous_task
        )

        console.print("[bold green]✨ 渲染结果:[/bold green]")
        console.print("="*60)
        console.print(rendered)
        console.print("="*60)

    except Exception as e:
        error(f"渲染失败: {e}")

@click.group()
def cli():
    """ChatCoder - Structured AI-assisted development CLI"""
    pass

# ----------------------------
# feature 命令组
# ----------------------------

@cli.group()
def feature():
    """Manage features (grouped development workflows)"""
    pass

@feature.command(name="list")
def feature_list():
    """List all features (grouped by feature_id)"""
    tasks_dir = get_tasks_dir()
    if not tasks_dir.exists():
        console.print("No tasks found.", style="yellow")
        return

    # 收集所有 feature_id
    feature_tasks = {}
    for json_file in tasks_dir.glob("*.json"):
        try:
            data = load_task_state(json_file.stem)  # task_id = filename without .json
            fid = data["feature_id"]
            if fid not in feature_tasks:
                feature_tasks[fid] = []
            feature_tasks[fid].append(data)
        except Exception as e:
            console.print(f"Warning: failed to load {json_file}: {e}", style="red")

    if not feature_tasks:
        console.print("No features found.", style="yellow")
        return

    # 显示表格
    table = Table(title="Features")
    table.add_column("Feature ID", style="cyan")
    table.add_column("Description", style="white")
    table.add_column("Tasks", style="magenta")
    table.add_column("Status", style="green")

    for fid, tasks in feature_tasks.items():
        desc = next((t["description"] for t in tasks if t["description"]), "N/A")
        task_count = len(tasks)
        statuses = {t["status"] for t in tasks}
        status = "completed" if all(s == "completed" for s in statuses) else "pending"
        table.add_row(fid, desc, str(task_count), status)

    console.print(table)

@feature.command(name="show")
@click.argument("feature_id")
def feature_show(feature_id: str):
    """Show all tasks under a specific feature, ordered by phase"""
    tasks_dir = get_tasks_dir()
    if not tasks_dir.exists():
        console.print("No tasks found.", style="yellow")
        return

    matching_tasks = []
    for json_file in tasks_dir.glob("*.json"):
        try:
            data = load_task_state(json_file.stem)
            if data["feature_id"] == feature_id:
                matching_tasks.append(data)
        except Exception as e:
            console.print(f"Warning: failed to load {json_file}: {e}", style="red")

    if not matching_tasks:
        console.print(f"No tasks found for feature: {feature_id}", style="red")
        return

    # 按 phase 排序
    #sorted_tasks = sorted(matching_tasks, key=lambda x: x.get("phase_order", 0))
    sorted_tasks = sorted(matching_tasks, key=lambda x: x["phase_order"])

    table = Table(title=f"Feature: {feature_id}")
    table.add_column("Task ID", style="cyan")
    table.add_column("Phase", style="blue")
    table.add_column("Template", style="white")
    table.add_column("Status", style="green")

    for task in sorted_tasks:
        table.add_row(
            task["task_id"],
            task["phase"],
            task["template"],
            task["status"]
        )

    console.print(table)

@feature.command(name="status")
def feature_status():
    """Show detailed status of all features"""
    tasks_dir = get_tasks_dir()
    if not tasks_dir.exists():
        console.print("No tasks found.", style="yellow")
        return

    feature_stats = {}
    for json_file in tasks_dir.glob("*.json"):
        try:
            data = load_task_state(json_file.stem)
            fid = data["feature_id"]
            if fid not in feature_stats:
                feature_stats[fid] = {"tasks": 0, "completed": 0, "phases": set(), "desc": data["description"]}
            feature_stats[fid]["tasks"] += 1
            if data["status"] == "completed":
                feature_stats[fid]["completed"] += 1
            feature_stats[fid]["phases"].add(data["phase"])
        except Exception as e:
            console.print(f"Warning: failed to load {json_file}: {e}", style="red")

    if not feature_stats:
        console.print("No features found.", style="yellow")
        return

    table = Table(title="Feature Status")
    table.add_column("Feature ID", style="cyan")
    table.add_column("Description", style="white", max_width=30)
    table.add_column("Tasks", style="magenta")
    table.add_column("Completed", style="green")
    table.add_column("Progress", style="yellow")
    table.add_column("Phases", style="blue")

    for fid, stats in feature_stats.items():
        total = stats["tasks"]
        done = stats["completed"]
        progress = f"{done}/{total}"
        bar = "█" * (done * 10 // max(total, 1)) + "░" * (10 - done * 10 // max(total, 1))
        table.add_row(
            fid,
            stats["desc"],
            str(total),
            str(done),
            f"[green]{progress}[/green] [{bar}]",
            ", ".join(sorted(stats["phases"]))
        )

    console.print(table)

@feature.command(name="delete")
@click.argument("feature_id")
@click.confirmation_option(prompt="Are you sure you want to delete this feature and all its tasks?")
def feature_delete(feature_id: str):
    """Delete a feature and all its associated tasks"""
    tasks_dir = get_tasks_dir()
    if not tasks_dir.exists():
        console.print("No tasks found.", style="yellow")
        return

    deleted = 0
    for json_file in tasks_dir.glob("*.json"):
        try:
            data = load_task_state(json_file.stem)
            if data["feature_id"] == feature_id:
                json_file.unlink()  # 删除文件
                deleted += 1
        except Exception as e:
            console.print(f"Warning: failed to delete {json_file}: {e}", style="red")

    if deleted > 0:
        console.print(f"Deleted {deleted} task(s) for feature: {feature_id}", style="green")
    else:
        console.print(f"No tasks found for feature: {feature_id}", style="yellow")

@cli.command(name="task-next")
def task_next():
    """Recommend the next task based on workflow schema"""
    tasks_dir = get_tasks_dir()
    if not tasks_dir.exists() or not any(tasks_dir.glob("*.json")):
        console.print("No tasks found. Run 'chatcoder start -d \"...\"' first.", style="yellow")
        return

    all_tasks = list_task_states()
    from collections import defaultdict
    features = defaultdict(list)
    for task in all_tasks:
        features[task["feature_id"]].append(task)

    recommendations = []
    for feature_id, tasks in features.items():
        status = get_feature_status(feature_id)

        if not status["next_phase"]:
            continue  # 已完成

        latest_completed = status["current_phase"]
        next_phase = status["next_phase"]
        workflow = status["workflow"]

        recommendations.append({
            "feature_id": feature_id,
            "description": tasks[0]["description"],
            "current_phase": latest_completed,
            "next_phase": next_phase,
            "workflow": workflow,
            "reason": f"Phase '{latest_completed}' is completed." if latest_completed else "Feature not started."
        })

    # 排序：优先推荐早期 phase
    schema = load_workflow_schema()
    phase_order = get_phase_order(schema)
    recommendations.sort(key=lambda x: phase_order.get(x["next_phase"], 99))

    if not recommendations:
        console.print("✅ All features are complete or in progress.", style="green")
        return

    rec = recommendations[0]
    next_phase_info = next(
        (p for p in schema["phases"] if p["name"] == rec["next_phase"]),
        {"title": rec["next_phase"].title()}
    )

    console.print("🚀 Recommended Next Task", style="bold green")
    console.print(f"Feature: [magenta]{rec['feature_id']}[/magenta]")
    console.print(f"Description: {rec['description']}")
    console.print(f"workflow: {rec['workflow']}")
    console.print(f"Current: [blue]{rec['current_phase'] or 'None'}[/blue] → Next: [yellow]{next_phase_info['title']} ({rec['next_phase']})[/yellow]")
    console.print(f"Reason: {rec['reason']}")

    suggestion = f"chatcoder task create --feature {rec['feature_id']} --phase {rec['next_phase']} --template {rec['next_phase']}"
    console.print(f"\n💡 Suggested command:")
    console.print(f"[dim]$[/dim] [cyan]{suggestion}[/cyan]")

@cli.command(name="task-create")
@click.option("--feature-id", "-f", required=True, help="Feature ID")
@click.option("--phase", "-p", required=True, help="Phase name (e.g., design, code)")
@click.option("--template", "-t", help="Template to use")
@click.option("--description", "-d", help="Override description")
def task_create(feature_id: str, phase: str, template: str, description: str = None):
    """Create a new task for a feature"""
    from chatcoder.core.workflow import load_workflow_schema
    from chatcoder.core.state import generate_task_id, save_task_state

    # 从任意任务中推断 workflow
    tasks = list_task_states()
    workflow_tasks = [t for t in tasks if t.get("feature_id") == feature_id]
    workflow_name = "default"
    if workflow_tasks:
        workflow_name = workflow_tasks[0].get("workflow", "default")

    try:
        schema = load_workflow_schema(workflow_name)
        valid_phases = [p["name"] for p in schema["phases"]]
        if phase not in valid_phases:
            console.print(f"❌ Phase '{phase}' not in workflow '{workflow_name}'", style="red")
            return
    except ValueError as e:
        console.print(f"❌ {e}", style="red")
        return

    task_id = generate_task_id()
    desc = description or f"Continue work on {feature_id}"

    if not template:
        template = phase

    save_task_state(
        task_id=task_id,
        template=template,
        description=desc,
        context={"source": "cli_task_create", "workflow": workflow_name},
        feature_id=feature_id,
        phase=phase,
        status="pending",
        workflow=workflow_name
    )

    console.print(f"✅ Created new task: {task_id}", style="green")
    console.print(f"🔧 Phase: {phase} | Template: {template}", style="blue")

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


@cli.command()
@click.option("--description", "-d", required=True, help="Feature description")
@click.option("--workflow", "-w", default="default", help="Workflow schema to use")
def start(description: str, workflow: str):
    """Start a new feature by creating the first task (e.g., analyze)"""
    try:
        schema = load_workflow_schema(workflow)
    except ValueError as e:
        console.print(f"❌ {e}", style="red")
        return

    # 获取第一个 phase
    first_phase = schema["phases"][0]
    phase_name = first_phase["name"]      # 如 "analyze"
    template_name = first_phase["template"]  # 如 "analyze"

    task_id = generate_task_id()
    feature_id = generate_feature_id(description)

    context = {
        "source": "cli_start",
        "workflow":  workflow
    }

    # TODO need FIX
    save_task_state(
        task_id=task_id,
        template=template_name,
        description=description,
        context=context,
        feature_id=feature_id,
        phase=phase_name,
        status="pending",
        workflow=workflow
    )

    console.print(f"🚀 Started new feature: {feature_id}", style="green")
    console.print(f"📝 Description: {description}", style="white")
    console.print(f"🔧 First task: {task_id} ({template_name})", style="blue")
    console.print(f"📄 Saved to: {get_tasks_dir() / f'{task_id}.json'}", style="dim")

@cli.group()
def workflow():
    """Manage workflows"""
    pass

@workflow.command(name="list")
def workflow_list():
    """List all available workflow templates"""
    from pathlib import Path
    workflows_dir = get_workflow_path()
    
    if not workflows_dir.exists():
        console.print("❌ No workflows directory found", style="red")
        return

    table = Table(title="Available Workflows", show_header=True, header_style="bold magenta")
    table.add_column("Name", style="cyan")
    table.add_column("Phases", style="green")
    table.add_column("Description", style="white")

    found = False
    for file in workflows_dir.glob("*.yaml"):
        name = file.stem  # 移除 .yaml
        try:
            schema = load_workflow_schema(name)
            phase_names = " → ".join([p["name"] for p in schema["phases"]])
            table.add_row(name, phase_names, schema.get("description", "-"))
            found = True
        except Exception as e:
            table.add_row(name, "-", f"❌ Invalid: {str(e)}")

    if found:
        console.print(table)
    else:
        console.print("📭 No valid workflow templates found", style="yellow")
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
