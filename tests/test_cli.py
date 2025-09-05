# tests/test_cli.py
import pytest
from click.testing import CliRunner
from chatcoder.cli import cli # 导入 CLI 应用

def test_cli_init_command(temp_project_dir):
    """测试 chatcoder init 命令 (基本运行)"""
    runner = CliRunner()
    # init 命令涉及交互，测试起来复杂。这里只测试基本运行和帮助。
    result = runner.invoke(cli, ['init', '--help'])
    assert result.exit_code == 0
    assert '初始化项目配置' in result.output

def test_cli_prompt_command_creates_task(temp_project_dir, task_orchestrator):
    """测试 chatcoder prompt 命令是否创建任务"""
    runner = CliRunner()
    result = runner.invoke(cli, ['prompt', 'prompt', 'analyze', 'Test feature description'])
    
    # 假设命令成功执行
    assert result.exit_code == 0
    
    # 验证是否创建了任务文件
    tasks = task_orchestrator.list_task_states()
    assert len(tasks) == 1
    assert tasks[0]['template'] == 'analyze'
    assert tasks[0]['description'] == 'Test feature description'
    # 可以添加更多断言来验证任务内容

# ... 可以为其他 CLI 命令添加类似的测试 ...
