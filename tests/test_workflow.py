# tests/test_commands.py
def test_workflow_list():
    from click.testing import CliRunner
    from chatcoder.cli import cli
    runner = CliRunner()
    result = runner.invoke(cli, ["workflow", "list"])
    assert result.exit_code == 0
    assert "default" in result.output
    assert "ai-agent" in result.output

def test_task_next():
    # 先创建一个任务
    from click.testing import CliRunner
    from chatcoder.cli import cli
    runner = CliRunner()
    result = runner.invoke(cli, ["task-create", "--feature-id", "feat-test", "--phase", "analyze"])
    assert result.exit_code == 0
    result = runner.invoke(cli, ["task-next"])
    assert result.exit_code == 0
    assert "Recommended Next Task" in result.output
    #assert "design" in result.output
