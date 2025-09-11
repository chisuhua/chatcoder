# chatcoder/cli.py
"""
ChatCoder CLI 主入口（重构版：通过服务层调用）
"""
import click
from pathlib import Path
from rich.panel import Panel
from rich.table import Table

# --- 导入新的服务类 ---
from chatcoder.core.chatcoder import ChatCoder

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
        ctx.obj = {'chatcoder_service': ChatCoder()}
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())

# ------------------------------
# 命令 1: init
# ------------------------------
@cli.command()
@click.pass_context
def init(ctx):
    """🔧 初始化项目配置"""
    heading("项目初始化")
    chatcoder_service: ChatCoder = ctx.obj['chatcoder_service']
    
    if chatcoder_service.is_project_initialized():
        if not confirm("配置已存在，重新初始化将覆盖。继续？", default=False):
            info("已取消")
            return
    try:
        success_init = chatcoder_service.initialize_project()
        if success_init:
            success("初始化完成！")
        else:
            error("初始化失败。")
    except Exception as e:
        error(f"初始化失败: {e}")

# ------------------------------
# feature 命令组
# ------------------------------
@cli.group()
def feature():
    """Manage features (grouped development workflows)"""
    pass

@feature.command(name="start")
@click.option("--description", "-d", required=True, help="Feature description")
@click.option("--workflow", "-w", default="default", help="Workflow schema to use")
@click.pass_context
def feature_start(ctx, description: str, workflow: str):
    """Start a new feature by creating the first task"""
    chatcoder_service: ChatCoder = ctx.obj['chatcoder_service']
    
    try:
        result = chatcoder_service.start_new_feature(description, workflow)
        feature_id = result['feature_id']
        success(f"🚀 Started new feature: {feature_id}")
        console.print(f"📝 Description: {description}", style="white")
        console.print(f"\n💡 Suggested next command:")
        console.print(f"[dim]$[/dim] [cyan]chatcoder task prompt {feature_id}[/cyan]")
    except Exception as e:
        error(f"Failed to start feature: {e}")

@feature.command(name="list")
@click.pass_context
def feature_list(ctx):
    """List all features (grouped by feature_id)"""
    heading("Features List")
    chatcoder_service: ChatCoder = ctx.obj['chatcoder_service']
    try:
        features_status = chatcoder_service.get_all_features_status()
        if not features_status:
            console.print("No features found.", style="yellow")
            return

        table = Table(title="Features")
        table.add_column("Feature ID", style="cyan")
        table.add_column("Description", style="white")
        table.add_column("Status", style="green")
        table.add_column("Progress", style="magenta")

        for feature_info in features_status:
             table.add_row(
                 feature_info.get("feature_id", "N/A"),
                 feature_info.get("description", "N/A"),
                 feature_info.get("status", "unknown"),
                 feature_info.get("progress", "N/A")
             )
        console.print(table)
    except Exception as e:
        error(f"Failed to list features: {e}")

@feature.command(name="status")
@click.argument("feature_id")
@click.pass_context
def feature_status(ctx, feature_id: str):
    """Show detailed status of a specific feature"""
    heading(f"Feature Status: {feature_id}")
    chatcoder_service: ChatCoder = ctx.obj['chatcoder_service']
    try:
        detail_status = chatcoder_service.get_feature_detail_status(feature_id)
        console.print_json(data=detail_status)
    except Exception as e:
        error(f"Failed to get status for feature {feature_id}: {e}")

# @feature.command(name="delete") ... (如果需要实现)

# ----------------------------
# task 命令组
# ----------------------------
@cli.group()
def task():
    """Manage tasks within a feature"""
    pass

@task.command(name="prompt")
@click.argument("feature_id")
@click.pass_context
def task_prompt(ctx, feature_id: str):
    """Generate prompt for the current active task of a feature"""
    heading(f"Generating prompt for feature: {feature_id}")
    chatcoder_service: ChatCoder = ctx.obj['chatcoder_service']
    
    try:
        prompt_content = chatcoder_service.generate_prompt_for_current_task(feature_id)
        console.print(Panel(prompt_content, title=f"📋 Prompt for {feature_id}", border_style="blue"))
    except Exception as e:
        error(f"Failed to generate prompt for feature {feature_id}: {e}")

@task.command(name="confirm")
@click.argument("feature_id")
@click.option("--summary", help="Summary of the AI response or work done")
@click.pass_context
def task_confirm(ctx, feature_id: str, summary: str):
    """Confirm the current task for a feature and advance the workflow"""
    chatcoder_service: ChatCoder = ctx.obj['chatcoder_service']
    
    try:
        result = chatcoder_service.confirm_task_and_advance(feature_id, summary)
        success(f"✅ Task for feature {feature_id} has been confirmed.")
        if result:
            next_phase = result.get('next_phase')
            reason = result.get('reason')
            if next_phase:
                info(f"Recommended next phase: {next_phase} (Reason: {reason})")
                console.print(f"\n💡 Suggested next command:")
                console.print(f"[dim]$[/dim] [cyan]chatcoder task prompt {feature_id}[/cyan] (for next phase)")
        else:
             info(f"Feature {feature_id} might be completed.")
    except Exception as e:
        error(f"Failed to confirm task for feature {feature_id}: {e}")

@task.command(name="preview")
@click.argument("phase_name")
@click.argument("feature_id")
@click.pass_context
def task_preview(ctx, phase_name: str, feature_id: str):
    """(Debug) Preview the prompt for a specific phase of a feature"""
    heading(f"Previewing prompt for phase '{phase_name}' of feature: {feature_id}")
    chatcoder_service: ChatCoder = ctx.obj['chatcoder_service']
    
    try:
        prompt_content = chatcoder_service.preview_prompt_for_phase(phase_name, feature_id)
        console.print(Panel(prompt_content, title=f"🖼️ Preview Prompt: {phase_name} ({feature_id})", border_style="green"))
    except Exception as e:
        error(f"Failed to preview prompt for phase '{phase_name}' of feature {feature_id}: {e}")

# ----------------------------
# workflow 命令组
# ----------------------------
@cli.group()
def workflow():
    """Manage workflows"""
    pass

@workflow.command(name="list")
@click.pass_context
def workflow_list(ctx):
    """List all available workflow templates"""
    heading("Available Workflows")
    chatcoder_service: ChatCoder = ctx.obj['chatcoder_service']
    
    try:
        workflow_names = chatcoder_service.list_available_workflows()
        if not workflow_names:
             console.print("No workflows found.", style="yellow")
             return

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Name", style="cyan")
        for name in workflow_names:
             table.add_row(name)
        console.print(table)
    except Exception as e:
         error(f"Failed to list workflows: {e}")

# ----------------------------
# 其他辅助命令
# ----------------------------
@cli.command(name="validate")
@click.pass_context
def config_validate(ctx):
    """验证 config.yaml 是否合法"""
    heading("Validating Configuration")
    chatcoder_service: ChatCoder = ctx.obj['chatcoder_service']
    
    try:
        validation_result = chatcoder_service.validate_configuration()
        is_valid = validation_result.get("is_valid", False)
        errors = validation_result.get("errors", [])
        
        if is_valid:
            success("🎉 配置文件验证通过！")
        else:
            error("❌ 配置文件验证失败！")
            for err in errors:
                console.print(f"  - {err}")
    except Exception as e:
        error(f"Validation failed unexpectedly: {e}")

# @cli.command() # context ...
# @cli.command() # status ...

# ------------------------------
# 主入口
# ------------------------------
if __name__ == '__main__':
    cli(obj={})
