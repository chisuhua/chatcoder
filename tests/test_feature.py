# tests/test_feature.py
from click.testing import CliRunner
from chatcoder.cli import cli
import json
from pathlib import Path

runner = CliRunner()


def test_feature_list_empty(tasks_dir):
    """测试 feature list 在无任务时的输出"""
    result = runner.invoke(cli, ["feature", "list"])
    assert result.exit_code == 0
    assert "No tasks found" in result.output or "No features found" in result.output

def test_feature_list_with_tasks(tasks_dir):
    """测试 feature list 能正确聚合 feature_id"""
    # 创建两个任务，属于同一个 feature
    from chatcoder.core.state import save_task_state

    save_task_state(
        task_id="task_001",
        template="analyze",
        description="User can post articles",
        context={},
        phase="analyze",
        status="completed",
    )
    save_task_state(
        task_id="task_002",
        template="design",
        description="User can post articles",
        context={},
        phase="design",
        status="pending",
    )

    # 创建另一个 feature
    save_task_state(
        task_id="task_003",
        template="analyze",
        description="Add dark mode",
        context={},
        phase="analyze",
        status="pending",
    )

    result = runner.invoke(cli, ["feature", "list"])
    assert result.exit_code == 0
    assert "feat_user_can_post_articles" in result.output
    assert "feat_add_dark_mode" in result.output
    assert "2" in result.output  # task_001 + task_002
    assert "1" in result.output  # task_003
    assert "pending" in result.output


def test_feature_show_success(tasks_dir):
    """测试 feature show 能正确显示任务列表"""
    from chatcoder.core.state import save_task_state

    save_task_state(
        task_id="task_001",
        template="analyze",
        description="User can post articles",
        context={},
        phase="analyze",
        status="completed",
    )
    save_task_state(
        task_id="task_002",
        template="design",
        description="User can post articles",
        context={},
        phase="design",
        status="pending",
    )

    result = runner.invoke(cli, ["feature", "show", "feat_user_can_post_articles"])
    assert result.exit_code == 0
    assert "Feature: feat_user_can_post_articles" in result.output
    assert "task_001" in result.output
    assert "task_002" in result.output
    assert "analyze" in result.output
    assert "design" in result.output
    assert "completed" in result.output
    assert "pending" in result.output


def test_feature_show_not_found(tasks_dir):
    """测试 feature show 在 feature 不存在时的错误提示"""
    result = runner.invoke(cli, ["feature", "show", "feat_nonexistent"])
    assert result.exit_code == 0  # 通常 CLI 不会因业务错误返回非0
    assert "No tasks found for feature" in result.output
    assert "feat_nonexistent" in result.output


def test_feature_show_empty(tasks_dir):
    """测试 feature show 在无任务时的行为"""
    result = runner.invoke(cli, ["feature", "show", "feat_empty"])
    assert result.exit_code == 0
    assert "No tasks found for feature" in result.output

def test_feature_list_all_completed(tasks_dir):
    """测试当所有任务都 completed 时，feature 状态为 completed"""
    from chatcoder.core.state import save_task_state

    save_task_state(
        task_id="task_004",
        template="analyze",
        description="Fix login bug",
        context={},
        phase="analyze",
        status="completed",
    )
    save_task_state(
        task_id="task_005",
        template="patch",
        description="Fix login bug",
        context={},
        phase="patch",
        status="completed",
    )

    result = runner.invoke(cli, ["feature", "list"])
    assert result.exit_code == 0
    assert "feat_fix_login_bug" in result.output
    assert "completed" in result.output  # ✅ 此时应该出现
    assert "pending" not in result.output.split("feat_fix_login_bug")[1]  # 在该行中不包含 pending
