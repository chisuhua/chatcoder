# chatcoder/tests/test_cli.py
"""
ChatCoder CLI 入口点单元测试
"""

import pytest
from unittest.mock import MagicMock

# --- 导入 CLI 应用 ---
# 通过 conftest.py 的 fixtures 来管理依赖

class TestChatCoderCLI:
    """测试 ChatCoder CLI 命令"""

    # --- 测试 CLI 主入口和帮助 ---
    def test_cli_entry_no_command_shows_help(self, runner):
        """测试不带任何命令运行 CLI 应显示帮助信息"""
        from chatcoder.cli import cli # 在测试函数内部导入以应用 patch
        result = runner.invoke(cli, [])
        assert result.exit_code == 0
        assert "Usage:" in result.output
        assert "ChatCoder - AI-Native Development Assistant" in result.output
        assert "init" in result.output
        assert "feature" in result.output
        assert "task" in result.output

    def test_cli_version(self, runner):
        """测试 --version 选项"""
        from chatcoder.cli import cli
        result = runner.invoke(cli, ['--version'])
        assert result.exit_code == 0
        assert "ChatCoder CLI v0.1.0" in result.output

    # --- 测试 init 命令 ---
    def test_init_command_success(self, runner, mock_cli_chatcoder):
        """测试 init 命令成功执行"""
        from chatcoder.cli import cli
        
        # 配置 mock 的行为
        mock_cli_chatcoder.is_project_initialized.return_value = False
        mock_cli_chatcoder.initialize_project.return_value = True

        result = runner.invoke(cli, ['init'], input='n\n') # 'n' 模拟用户拒绝覆盖

        assert result.exit_code == 0
        assert "项目初始化" in result.output
        assert "初始化完成！" in result.output
        # 验证 mock 方法被调用
        mock_cli_chatcoder.initialize_project.assert_called_once_with(interactive=True)

    # --- 测试 feature 命令组 ---
    def test_feature_start_command_success(self, runner, mock_cli_chatcoder):
        """测试 feature start 命令成功执行"""
        from chatcoder.cli import cli
        
        description = "实现用户登录"
        workflow = "default"
        expected_feature_id = "feat_user_login_123"

        # 配置 mock 返回值
        mock_cli_chatcoder.start_new_feature.return_value = {
            "feature_id": expected_feature_id,
            "description": description
        }

        result = runner.invoke(cli, ['feature', 'start', '-d', description, '-w', workflow])

        assert result.exit_code == 0
        assert f"Started new feature: {expected_feature_id}" in result.output
        assert description in result.output
        assert "Suggested next command:" in result.output
        assert f"chatcoder task prompt {expected_feature_id}" in result.output
        # 验证 mock 方法被调用及参数
        mock_cli_chatcoder.start_new_feature.assert_called_once_with(description, workflow)

    # --- 测试 task 命令组 ---
    def test_task_prompt_command_success(self, runner, mock_cli_chatcoder):
        """测试 task prompt <feature_id> 命令成功执行"""
        from chatcoder.cli import cli
        
        feature_id = "feat_prompt_test"
        mock_prompt_content = "这是为特性生成的 AI 提示词内容..."
        mock_cli_chatcoder.generate_prompt_for_current_task.return_value = mock_prompt_content

        result = runner.invoke(cli, ['task', 'prompt', feature_id])

        assert result.exit_code == 0
        assert f"Generating prompt for feature: {feature_id}" in result.output
        # 由于 rich 的输出可能不完全被捕获，重点检查方法调用
        assert mock_prompt_content in result.output
        mock_cli_chatcoder.generate_prompt_for_current_task.assert_called_once_with(feature_id)

    # --- 测试 validate 命令 ---
    def test_validate_command_success(self, runner, mock_cli_chatcoder):
        """测试 validate 命令成功执行"""
        from chatcoder.cli import cli
        
        mock_cli_chatcoder.validate_configuration.return_value = {"is_valid": True, "errors": []}

        result = runner.invoke(cli, ['validate'])

        assert result.exit_code == 0
        assert "Validating Configuration" in result.output
        assert "配置文件验证通过！" in result.output
        mock_cli_chatcoder.validate_configuration.assert_called_once()

    # --- 其他 CLI 命令测试可以类似添加 ---
    # ... (为其他 CLI 命令添加测试)
