# chatcoder/cli
"""
ChatCoder CLI 主入口（重构版：通过 Thinker 和 Coder 服务层调用）
"""
import click
import json
import yaml # 用于加载配置文件
from datetime import datetime
from pathlib import Path

from rich.panel import Panel
from rich.table import Table

# --- 导入新的服务类 ---
# 注意：导入路径已根据文件重命名进行更新
from chatcoder.core.thinker import Thinker # <-- 从 thinker.py 导入 Thinker
from chatcoder.core.coder import Coder    # <-- 从 coder.py 导入 Coder

# --- 导入其他必要的模块 ---
from chatcoder.utils.console import (
    console, info, success, warning, error,
    heading, show_welcome, confirm
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
# 注意：这部分假设 init.py 的逻辑没有改变
try:
    from chatcoder.init import init_project as perform_init_project, validate_config_content
except ImportError:
    try:
        from chatcoder.core.init import init_project as perform_init_project, validate_config_content
    except ImportError:
        def perform_init_project():
            raise NotImplementedError("init_project function not found.")
        def validate_config_content(*args, **kwargs):
            raise NotImplementedError("validate_config_content function not found.")
        error("Failed to import initialization functions. Please check your installation.")

@cli.command()
@click.pass_context
def init(ctx):
    """🔧 Initialize project configuration"""
    heading("Project Initialization")
    state_dir = Path(".chatcoder")
    config_file = state_dir / "config.yaml"
    context_file = state_dir / "context.yaml"

    if state_dir.exists() and context_file.exists():
        if not confirm("Configuration already exists. Re-initializing will overwrite. Continue?", default=False):
            info("Cancelled.")
            return
    try:
        config_content, context_content = perform_init_project()

        state_dir.mkdir(exist_ok=True)
        # 确保存储实例的目录也存在
        (state_dir / "workflow_instances").mkdir(exist_ok=True)

        if config_file.exists():
            if confirm(f"{config_file} already exists. Overwrite?", default=False):
                config_file.write_text(config_content, encoding="utf-8")
                success(f"Updated: {config_file}")
            else:
                info(f"Skipped update: {config_file}")
        else:
             config_file.write_text(config_content, encoding="utf-8")
             success(f"Generated: {config_file}")

        if context_file.exists():
            if confirm(f"{context_file} already exists. Overwrite?", default=False):
                context_file.write_text(context_content, encoding="utf-8")
                success(f"Updated: {context_file}")
            else:
                info(f"Skipped update: {context_file}")
        else:
             context_file.write_text(context_content, encoding="utf-8")
             success(f"Generated: {context_file}")

        success("Initialization complete!")
    except Exception as e:
        error(f"Initialization failed: {e}")

# ------------------------------
# 辅助函数：加载 Thinker 服务
# ------------------------------

def _load_thinker_service() -> Thinker: # <-- 函数名更新
    """
    Helper function: Load config files and instantiate the Thinker service.
    """
    config_file = Path(".chatcoder") / "config.yaml"
    context_file = Path(".chatcoder") / "context.yaml"
    storage_dir = Path(".chatcoder") / "workflow_instances" # Add storage_dir

    if not config_file.exists() or not context_file.exists():
        error("Configuration files missing. Please run `chatcoder init` first.")
        raise click.Abort()

    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f) or {}
    except Exception as e:
        error(f"Failed to read config.yaml: {e}")
        raise click.Abort()

    try:
        with open(context_file, 'r', encoding='utf-8') as f:
            context_data = yaml.safe_load(f) or {}
    except Exception as e:
        error(f"Failed to read context.yaml: {e}")
        raise click.Abort()

    # Instantiate the new Thinker service
    return Thinker(config_data=config_data, context_data=context_data, storage_dir=str(storage_dir))

# ------------------------------
# 命令 2: context (显示原始配置文件内容)
# ------------------------------

@cli.command(name="context") # Rename to avoid conflict with group name if needed, or keep as is
@click.pass_context
def show_context(ctx):
    """📚 View raw project context (from .chatcoder/config.yaml and .chatcoder/context.yaml)"""
    heading("Project Raw Configuration and Context")
    try:
        config_file = Path(".chatcoder") / "config.yaml"
        context_file = Path(".chatcoder") / "context.yaml"
        config_data = {}
        context_data = {}
        if config_file.exists():
             with open(config_file, 'r', encoding='utf-8') as f:
                 config_data = yaml.safe_load(f) or {}
        if context_file.exists():
             with open(context_file, 'r', encoding='utf-8') as f:
                 context_data = yaml.safe_load(f) or {}

        # Display config.yaml content
        if config_data:
            console.print("[bold cyan]### config.yaml Content:[/bold cyan]")
            console.print_json(data=config_data)
        else:
            console.print("[yellow]config.yaml not found or empty.[/yellow]")

        # Display context.yaml content
        if context_data:
            console.print("\n[bold cyan]### context.yaml Content:[/bold cyan]")
            console.print_json(data=context_data)
        else:
             console.print("\n[yellow]context.yaml not found or empty.[/yellow]")

    except Exception as e:
        error(f"Failed to read or display configuration files: {e}")
        raise click.Abort()

# ------------------------------
# feature 命令组 (主要入口)
# ------------------------------
@cli.group()
def feature():
    """🧠 Manage features (logical groupings of development workflows)"""
    pass

@feature.command(name="start")
@click.option("--description", "-d", required=True, help="Feature description")
@click.option("--workflow", "-w", default="default", help="Workflow schema to use")
@click.pass_context
def feature_start(ctx, description: str, workflow: str):
    """🚀 Start a new feature workflow"""
    thinker_service = _load_thinker_service()
    try:
        result = thinker_service.start_new_feature(description, workflow)
        feature_id = result['feature_id']
        instance_id = result.get('instance_id', 'N/A')
        success(f"Started new feature workflow: {feature_id}")
        if instance_id != 'N/A':
            info(f"   Initial Instance ID: {instance_id}")
        console.print(f"📝 Description: {description}", style="white")
        console.print(f"\n💡 Suggested next command:")
        console.print(f"[dim]$[/dim] [cyan]chatcoder task prompt --feature {feature_id}[/cyan]")
    except Exception as e:
        error(f"Failed to start feature: {e}")

@feature.command(name="list")
@click.pass_context
def feature_list(ctx):
    """📋 List all features"""
    thinker_service = _load_thinker_service()
    heading("Features List")
    try:
        feature_ids = thinker_service.list_all_features()
        if not feature_ids:
            console.print("No features found.", style="yellow")
            return

        table = Table(title="Features")
        table.add_column("Feature ID", style="cyan")
        table.add_column("Instances", style="blue")

        for fid in feature_ids:
            try:
                instances_info = thinker_service.get_feature_instances(fid)
                instance_count = len(instances_info)
            except Exception:
                instance_count = "Error"
            table.add_row(fid, str(instance_count))

        console.print(table)
    except Exception as e:
        error(f"Failed to list features: {e}")

@feature.command(name="status")
@click.argument("feature_id")
@click.pass_context
def feature_status(ctx, feature_id: str):
    """📊 Show status of all instances associated with a feature"""
    heading(f"Instances for Feature: {feature_id}")
    thinker_service = _load_thinker_service()
    try:
        instances_status = thinker_service.get_feature_instances(feature_id)

        if not instances_status:
            console.print("No instances found for this feature.", style="yellow")
            return

        table = Table(title=f"Instances for Feature {feature_id}")
        table.add_column("Instance ID", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Current Phase", style="magenta")
        table.add_column("Progress", style="blue")
        table.add_column("Updated At", style="white")

        for instance_info in instances_status:
             updated_at_ts = instance_info.get('updated_at', 0)
             try:
                 updated_at_str = datetime.fromtimestamp(updated_at_ts).strftime('%Y-%m-%d %H:%M:%S')
             except:
                 updated_at_str = "Invalid Date"

             table.add_row(
                 instance_info.get("instance_id", "N/A"),
                 instance_info.get("status", "unknown"),
                 instance_info.get("current_phase", "N/A"),
                 f"{int(float(instance_info.get('progress', 0)) * 100)}%" if instance_info.get('progress') else "N/A",
                 updated_at_str
             )
        console.print(table)

    except Exception as e:
        error(f"Failed to get status for feature {feature_id}: {e}")

@feature.command(name="delete")
@click.argument("feature_id")
@click.pass_context
def feature_delete(ctx, feature_id: str):
    """🗑️ Delete a feature and all its associated instances"""
    thinker_service = _load_thinker_service()
    try:
        success_deleted = thinker_service.delete_feature(feature_id)
        if success_deleted:
            success(f"Feature '{feature_id}' and its instances have been deleted.")
        else:
             info(f"No instances found for feature '{feature_id}' or deletion was not fully successful.")
    except Exception as e:
         error(f"Failed to delete feature {feature_id}: {e}")

# ----------------------------
# feature task 子命令组 (针对特定 feature 的任务操作)
# ----------------------------
@feature.group(name="task")
@click.argument("feature_id")
@click.pass_context
def feature_task(ctx, feature_id: str):
    """🛠️ Manage tasks within a specific feature (targets active instance)"""
    ctx.ensure_object(dict)
    ctx.obj['FEATURE_ID'] = feature_id
    thinker_service = _load_thinker_service()
    ctx.obj['THINKER_SERVICE'] = thinker_service
    # Resolve active instance ID here for convenience in subcommands
    try:
        active_instance_id = thinker_service.get_active_instance_for_feature(feature_id)
        if not active_instance_id:
            raise click.ClickException(f"No active workflow instance found for feature '{feature_id}'.")
        ctx.obj['ACTIVE_INSTANCE_ID'] = active_instance_id
    except Exception as e:
        raise click.ClickException(f"Error resolving active instance for feature '{feature_id}': {e}")

@feature_task.command(name="status")
@click.pass_context
def feature_task_status(ctx):
    """🔍 Show detailed status of the active task instance for the feature"""
    feature_id = ctx.obj['FEATURE_ID']
    instance_id = ctx.obj['ACTIVE_INSTANCE_ID']
    heading(f"Active Task Instance Status for Feature '{feature_id}' (ID: {instance_id})")
    thinker_service = ctx.obj['THINKER_SERVICE']
    try:
        detail_status = thinker_service.get_instance_detail_status(instance_id)
        console.print_json(data=detail_status)
    except Exception as e:
        error(f"Failed to get status for instance {instance_id}: {e}")

@feature_task.command(name="prompt")
@click.pass_context
def feature_task_prompt(ctx):
    """🧾 Generate prompt for the current task of the feature's active instance"""
    feature_id = ctx.obj['FEATURE_ID']
    instance_id = ctx.obj['ACTIVE_INSTANCE_ID']
    heading(f"Generating prompt for feature '{feature_id}' (active instance: {instance_id})")
    thinker_service = ctx.obj['THINKER_SERVICE']
    try:
        prompt_content = thinker_service.generate_prompt_for_current_task(instance_id)
        console.print(Panel(prompt_content, title=f"📋 Prompt for {feature_id} (Instance: {instance_id})", border_style="blue"))
    except Exception as e:
        error(f"Failed to generate prompt for instance {instance_id}: {e}")

@feature_task.command(name="confirm")
@click.option("--summary", help="Summary of the AI response or work done")
@click.pass_context
def feature_task_confirm(ctx, summary: str):
    """✅ Confirm the current task for the feature's active instance and advance the workflow"""
    feature_id = ctx.obj['FEATURE_ID']
    instance_id = ctx.obj['ACTIVE_INSTANCE_ID']
    thinker_service = ctx.obj['THINKER_SERVICE']
    try:
        result = thinker_service.confirm_task_and_advance(instance_id, summary)
        success(f"✅ Task for instance {instance_id} (feature '{feature_id}') has been confirmed.")
        if result:
            next_phase = result.get('next_phase')
            status = result.get('status')
            returned_feature_id = result.get('feature_id')
            if next_phase:
                info(f"Next phase: {next_phase} (Status: {status})")
                console.print(f"\n💡 Suggested next command:")
                console.print(f"[dim]$[/dim] [cyan]chatcoder task prompt --feature {feature_id}[/cyan] (for next phase)")
            else:
                 info(f"Workflow instance {instance_id} (Feature: {returned_feature_id}) might be completed.")
        else:
             info("Advance was cancelled by user.")
    except Exception as e:
        error(f"Failed to confirm task for instance {instance_id}: {e}")

@feature_task.command(name="preview")
@click.argument("phase_name")
@click.option("--description", "-d", default="", help="Task description for the preview")
@click.pass_context
def feature_task_preview(ctx, phase_name: str, description: str):
    """🖼️ Preview the prompt for a specific phase of the feature's active instance"""
    feature_id = ctx.obj['FEATURE_ID']
    instance_id = ctx.obj['ACTIVE_INSTANCE_ID']
    heading(f"Previewing prompt for phase '{phase_name}' of feature '{feature_id}' (instance: {instance_id})")
    thinker_service = ctx.obj['THINKER_SERVICE']
    try:
        task_desc = description if description else f"Preview task in phase '{phase_name}'"
        prompt_content = thinker_service.preview_prompt_for_phase(instance_id, phase_name, task_desc)
        console.print(Panel(prompt_content, title=f"🖼️ Preview Prompt: {phase_name} ({feature_id})", border_style="green"))
    except Exception as e:
        error(f"Failed to preview prompt for phase '{phase_name}' of instance {instance_id}: {e}")

@feature_task.command(name="apply")
@click.argument("response_file", type=click.Path(exists=True))
@click.pass_context
def feature_task_apply(ctx, response_file: str):
    """💾 Apply an AI response file to the current task of the feature's active instance"""
    feature_id = ctx.obj['FEATURE_ID']
    instance_id = ctx.obj['ACTIVE_INSTANCE_ID']
    heading(f"Applying AI response for feature '{feature_id}' (instance: {instance_id})")
    thinker_service = ctx.obj['THINKER_SERVICE'] # Needed to pass to Coder constructor
    # 3. 实例化 Coder 服务
    coder_service = Coder(thinker_service) # <-- 实例化 Coder，传入 Thinker

    # 4. 读取 AI 响应文件内容
    try:
        response_content = Path(response_file).read_text(encoding='utf-8')
    except FileNotFoundError:
        error(f"AI response file not found: {response_file}")
        raise click.Abort()
    except Exception as e:
        error(f"Failed to read AI response file '{response_file}': {e}")
        raise click.Abort()

    # 5. 调用 Coder 的 apply_task 方法
    try:
        success_applied = coder_service.apply_task(instance_id, response_content)

        # 6. 根据结果输出信息
        if success_applied:
            success(f"AI response from '{response_file}' applied to instance '{instance_id}' (feature '{feature_id}').")
        else:
             warning(f"Apply task returned issues or partial success for instance {instance_id}. Check logs for details.")

    except Exception as e:
         error(f"Failed to apply AI response for instance {instance_id}: {e}")
         raise click.Abort()

# ----------------------------
# task 命令组 (直接使用 instance_id, 保留用于高级/调试用途)
# ----------------------------
@cli.group()
def task():
    """⚙️ Manage tasks directly by instance ID (advanced/debugging)"""
    pass

# --- 通用选项装饰器，用于 task 子命令 ---
def common_task_options(f):
    """为 task 子命令添加通用的 instance_id 或 feature_id 选项"""
    f = click.option("--id", "instance_id", help="The workflow instance ID")(f)
    f = click.option("--feature", "feature_id", help="The feature ID (will use its active instance)")(f)
    return f

def _resolve_instance_id(thinker_service: Thinker, instance_id: str, feature_id: str) -> str:
    """Helper to resolve instance_id from either direct ID or feature ID."""
    if not instance_id and not feature_id:
        raise click.UsageError("Missing option '--id' or '--feature'.")
    if instance_id and feature_id:
        raise click.UsageError("Only one of '--id' or '--feature' can be provided.")

    if feature_id:
        active_id = thinker_service.get_active_instance_for_feature(feature_id)
        if not active_id:
            raise click.ClickException(f"Could not find active instance for feature '{feature_id}'.")
        info(f"Using active instance '{active_id}' for feature '{feature_id}'.")
        return active_id
    return instance_id # Direct instance_id provided

@task.command(name="prompt")
@common_task_options
@click.pass_context
def task_prompt(ctx, instance_id: str, feature_id: str):
    """🧾 Generate prompt for the current task of a workflow instance"""
    thinker_service = _load_thinker_service()
    instance_id = _resolve_instance_id(thinker_service, instance_id, feature_id)
    heading(f"Generating prompt for instance: {instance_id}")
    try:
        prompt_content = thinker_service.generate_prompt_for_current_task(instance_id)
        console.print(Panel(prompt_content, title=f"📋 Prompt for {instance_id}", border_style="blue"))
    except Exception as e:
        error(f"Failed to generate prompt for instance {instance_id}: {e}")

@task.command(name="confirm")
@common_task_options
@click.option("--summary", help="Summary of the AI response or work done")
@click.pass_context
def task_confirm(ctx, instance_id: str, feature_id: str, summary: str):
    """✅ Confirm the current task for an instance and advance the workflow"""
    thinker_service = _load_thinker_service()
    instance_id = _resolve_instance_id(thinker_service, instance_id, feature_id)
    try:
        result = thinker_service.confirm_task_and_advance(instance_id, summary)
        success(f"✅ Task for instance {instance_id} has been confirmed.")
        if result:
            next_phase = result.get('next_phase')
            status = result.get('status')
            feature_id_result = result.get('feature_id')
            if next_phase:
                info(f"Next phase: {next_phase} (Status: {status})")
                console.print(f"\n💡 Suggested next command:")
                console.print(f"[dim]$[/dim] [cyan]chatcoder task prompt --id {instance_id}[/cyan] (for next phase)")
            else:
                 info(f"Workflow instance {instance_id} (Feature: {feature_id_result}) might be completed.")
        else:
             info("Advance was cancelled by user.")
    except Exception as e:
        error(f"Failed to confirm task for instance {instance_id}: {e}")

@task.command(name="preview")
@click.argument("phase_name")
@common_task_options
@click.option("--description", "-d", default="", help="Task description for the preview")
@click.pass_context
def task_preview(ctx, phase_name: str, instance_id: str, feature_id: str, description: str):
    """🖼️ Preview the prompt for a specific phase of an instance"""
    thinker_service = _load_thinker_service()
    instance_id = _resolve_instance_id(thinker_service, instance_id, feature_id)
    heading(f"Previewing prompt for phase '{phase_name}' of instance: {instance_id}")
    try:
        task_desc = description if description else f"Preview task in phase '{phase_name}'"
        prompt_content = thinker_service.preview_prompt_for_phase(instance_id, phase_name, task_desc)
        console.print(Panel(prompt_content, title=f"🖼️ Preview Prompt: {phase_name} ({instance_id})", border_style="green"))
    except Exception as e:
        error(f"Failed to preview prompt for phase '{phase_name}' of instance {instance_id}: {e}")

@task.command(name="apply")
@common_task_options
@click.argument("response_file", type=click.Path(exists=True))
@click.pass_context
def task_apply(ctx, instance_id: str, feature_id: str, response_file: str):
    """💾 Apply an AI response file to the current task of an instance"""
    thinker_service = _load_thinker_service()
    instance_id = _resolve_instance_id(thinker_service, instance_id, feature_id)
    heading(f"Applying AI response for instance: {instance_id}")
    # 3. 实例化 Coder 服务
    coder_service = Coder(thinker_service) # <-- 实例化 Coder，传入 Thinker

    # 4. 读取 AI 响应文件内容
    try:
        response_content = Path(response_file).read_text(encoding='utf-8')
    except FileNotFoundError:
        error(f"AI response file not found: {response_file}")
        raise click.Abort()
    except Exception as e:
        error(f"Failed to read AI response file '{response_file}': {e}")
        raise click.Abort()

    # 5. 调用 Coder 的 apply_task 方法
    try:
        success_applied = coder_service.apply_task(instance_id, response_content)

        # 6. 根据结果输出信息
        if success_applied:
            success(f"AI response from '{response_file}' applied to instance '{instance_id}'.")
        else:
             warning(f"Apply task returned issues or partial success for instance {instance_id}. Check logs for details.")

    except Exception as e:
         error(f"Failed to apply AI response for instance {instance_id}: {e}")
         raise click.Abort()

# ----------------------------
# instance 命令组 (保留用于详细状态查看)
# ----------------------------
@cli.group()
def instance():
    """🔬 Inspect individual workflow instances (debugging)"""
    pass

@instance.command(name="status")
@click.argument("instance_id")
@click.pass_context
def instance_status(ctx, instance_id: str):
    """🔍 Show detailed status of a specific workflow instance"""
    heading(f"Instance Status: {instance_id}")
    thinker_service = _load_thinker_service()
    try:
        detail_status = thinker_service.get_instance_detail_status(instance_id)
        console.print_json(data=detail_status)
    except Exception as e:
        error(f"Failed to get status for instance {instance_id}: {e}")

# ----------------------------
# workflow 命令组
# ----------------------------
@cli.group()
def workflow():
    """🔄 Manage workflow definitions"""
    pass

@workflow.command(name="list")
@click.pass_context
def workflow_list(ctx):
    """📄 List all available workflow templates"""
    heading("Available Workflows")
    # ChatCoder v0.1 中移除了 list_available_workflows，直接扫描目录
    workflows_dir = Path("ai-prompts") / "workflows"

    try:
        if not workflows_dir.exists():
             console.print(f"Workflows directory not found at {workflows_dir}", style="yellow")
             return

        workflow_files = list(workflows_dir.glob("*.yaml"))
        if not workflow_files:
             console.print("No workflows found.", style="yellow")
             return

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Name", style="cyan")
        for wf_file in workflow_files:
             table.add_row(wf_file.stem)
        console.print(table)
    except Exception as e:
         error(f"Failed to list workflows: {e}")

# ----------------------------
# 其他辅助命令
# ----------------------------
@cli.command(name="validate")
@click.pass_context
def config_validate(ctx):
    """✅ Validate config.yaml syntax"""
    heading("Validating Configuration")
    try:
        config_file = Path(".chatcoder") / "config.yaml"
        content = config_file.read_text(encoding="utf-8")
        validate_config_content(content)
        success("Configuration file validated successfully!")
    except Exception as e:
        error(f"Validation failed unexpectedly: {e}")

# ------------------------------
# 主入口
# ------------------------------
if __name__ == '__main__':
    cli(obj={})
