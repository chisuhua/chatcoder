# chatcoder/tests/test_cli.py
"""
ChatCoder CLI 入口点单元测试
"""

import pytest
from unittest.mock import MagicMock

# --- 导入 CLI 应用 ---
# Dependencies are managed via conftest.py fixtures

class TestChatCoderCLI:
    """测试 ChatCoder CLI 命令"""

    # --- 测试 CLI 主入口和帮助 ---
    def test_cli_entry_no_command_shows_help(self, runner):
        """测试不带任何命令运行 CLI 应显示帮助信息"""
        from chatcoder.cli import cli
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
    # Note: init command involves file I/O and calling init_project function.
    # Testing it fully would require mocking 'chatcoder.init' module functions like 'perform_init_project'
    # and 'validate_config_content', and managing temporary directories/files.
    # This is a simplified test focusing on the command structure and basic flow.
    # A more comprehensive test would involve those mocks.
    def test_init_command_basic_flow(self, runner, tmp_path, monkeypatch):
        """测试 init 命令的基本执行流程 (简化版)"""
        from chatcoder.cli import cli
        
        # Change to a temporary directory for this test
        monkeypatch.chdir(tmp_path)
        
        # Mock the init_project function from chatcoder.init (assuming it's moved there)
        # We need to patch where it's used, which is inside cli.py's local import scope.
        # Let's assume cli.py does 'from chatcoder.init import init_project as perform_init_project'
        # So we patch chatcoder.cli.perform_init_project
        mock_init_content = ("# Mock config content\nkey: value\n", "# Mock context content\nproject: test\n")
        
        with pytest.MonkeyPatch().context() as m:
            # Patch the specific function called by cli.py
            m.setattr('chatcoder.cli.perform_init_project', lambda: mock_init_content)
            m.setattr('chatcoder.cli.validate_config_content', lambda x: None) # Mock validation
            
            # Simulate user declining overwrite if dir exists (though it shouldn't in tmp_path)
            # But let's test the overwrite path too by pre-creating the dir
            (tmp_path / ".chatcoder").mkdir()
            (tmp_path / ".chatcoder" / "context.yaml").write_text("old: content")
            
            # Run init command, simulate user confirming overwrite
            result = runner.invoke(cli, ['init'], input='y\ny\n') # Confirm overwrite for both files if prompted

            assert result.exit_code == 0
            assert "初始化完成！" in result.output
            assert (tmp_path / ".chatcoder" / "config.yaml").exists()
            assert (tmp_path / ".chatcoder" / "context.yaml").exists()
            # Further assertions could check file contents match mock_init_content

    # --- 测试 feature 命令组 ---
    def test_feature_start_command_success(self, runner, mock_cli_chatcoder):
        """测试 feature start 命令成功执行"""
        from chatcoder.cli import cli
        
        description = "实现用户登录"
        workflow = "default"
        expected_feature_id = "feat_new_123"

        result = runner.invoke(cli, ['feature', 'start', '-d', description, '-w', workflow])

        assert result.exit_code == 0
        assert f"Started new feature: {expected_feature_id}" in result.output
        assert description in result.output
        assert "Suggested next command:" in result.output
        mock_cli_chatcoder.start_new_feature.assert_called_once_with(description, workflow)

    def test_feature_list_command_success(self, runner, mock_cli_chatcoder):
        """测试 feature list 命令成功执行"""
        from chatcoder.cli import cli

        result = runner.invoke(cli, ['feature', 'list'])

        assert result.exit_code == 0
        assert "Features List" in result.output
        assert "feat_1" in result.output
        assert "Test Feature 1" in result.output
        assert "in_progress" in result.output
        mock_cli_chatcoder.get_all_features_status.assert_called_once()

    # --- 测试 task 命令组 ---
    def test_task_prompt_command_success(self, runner, mock_cli_chatcoder):
        """测试 task prompt <feature_id> 命令成功执行"""
        from chatcoder.cli import cli
        
        feature_id = "feat_prompt_test"
        mock_prompt_content = "这是为特性生成的 AI 提示词内容..."

        result = runner.invoke(cli, ['task', 'prompt', feature_id])

        assert result.exit_code == 0
        assert f"Generating prompt for feature: {feature_id}" in result.output
        # Check if prompt content is in the output (might be in a Panel, so check substring)
        assert mock_prompt_content in result.output
        mock_cli_chatcoder.generate_prompt_for_current_task.assert_called_once_with(feature_id)

    def test_task_confirm_command_success_with_next(self, runner, mock_cli_chatcoder):
        """测试 task confirm <feature_id> 命令成功执行并有下一步推荐"""
        from chatcoder.cli import cli
        
        feature_id = "feat_confirm_test"
        summary = "已完成分析"
        expected_next_phase = "design"

        result = runner.invoke(cli, ['task', 'confirm', feature_id, '--summary', summary])

        assert result.exit_code == 0
        assert f"Task for feature {feature_id} has been confirmed." in result.output
        assert f"Recommended next phase: {expected_next_phase}" in result.output
        mock_cli_chatcoder.confirm_task_and_advance.assert_called_once_with(feature_id, summary)

    def test_task_preview_command_success(self, runner, mock_cli_chatcoder):
        """测试 task preview <phase_name> <feature_id> 命令成功执行"""
        from chatcoder.cli import cli
        
        phase_name = "test"
        feature_id = "feat_preview_abc"
        mock_preview_content = "这是预览的测试阶段提示词..."

        result = runner.invoke(cli, ['task', 'preview', phase_name, feature_id])

        assert result.exit_code == 0
        assert f"Previewing prompt for phase '{phase_name}' of feature: {feature_id}" in result.output
        assert mock_preview_content in result.output
        mock_cli_chatcoder.preview_prompt_for_phase.assert_called_once_with(phase_name, feature_id)

    # --- 测试 task apply 命令 ---
    def test_task_apply_command_success(self, runner, mock_cli_chatcoder, tmp_path):
        """测试 task apply <feature_id> <response_file> 命令成功执行"""
        from chatcoder.cli import cli
        
        feature_id = "feat_apply_xyz"
        response_file = tmp_path / "ai_response.txt"
        response_content = "This is the AI's response to be applied."
        response_file.write_text(response_content, encoding='utf-8')
        
        # Mock the apply_task method to return success
        mock_cli_chatcoder.apply_task.return_value = True

        result = runner.invoke(cli, ['task', 'apply', feature_id, str(response_file)])

        assert result.exit_code == 0
        assert f"Applying AI response for feature: {feature_id}" in result.output
        assert f"AI response from '{response_file}' applied to feature '{feature_id}'." in result.output
        # Verify the ChatCoder service's apply_task was called with correct content
        mock_cli_chatcoder.apply_task.assert_called_once_with(feature_id, response_content)

    def test_task_apply_command_file_not_found(self, runner, mock_cli_chatcoder):
        """测试 task apply 命令处理文件不存在的情况"""
        from chatcoder.cli import cli
        
        feature_id = "feat_apply_err"
        non_existent_file = "non_existent_response.txt"

        result = runner.invoke(cli, ['task', 'apply', feature_id, non_existent_file])

        assert result.exit_code == 0 # CLI handles the error gracefully
        assert f"Applying AI response for feature: {feature_id}" in result.output
        assert f"AI response file not found: {non_existent_file}" in result.output
        # apply_task should not have been called
        mock_cli_chatcoder.apply_task.assert_not_called()

    # --- 测试 workflow 命令组 ---
    def test_workflow_list_command_success(self, runner, mock_cli_chatcoder):
        """测试 workflow list 命令成功执行"""
        from chatcoder.cli import cli

        result = runner.invoke(cli, ['workflow', 'list'])

        assert result.exit_code == 0
        assert "Available Workflows" in result.output
        assert "default" in result.output
        assert "custom" in result.output
        mock_cli_chatcoder.list_available_workflows.assert_called_once()

    # --- 测试 validate 命令 ---
    # Similar to init, validate involves calling external functions.
    # A basic test checks the command structure.
    def test_validate_command_basic_call(self, runner, mock_cli_chatcoder):
        """测试 validate 命令被调用 (简化版)"""
        from chatcoder.cli import cli
        
        # Mock the validate method or the underlying config check if it existed on the service
        # For now, assume _load_chatcoder_service works and the service has a validate method
        # or the cli calls a function. We mock the service creation part.
        
        result = runner.invoke(cli, ['validate'])

        # Assert based on mock_cli_chatcoder setup or expected behavior
        # If _load_chatcoder_service is called and then a method, the mock setup handles it.
        # This test ensures the command path is executed.
        assert result.exit_code == 0 # Or check specific output if mocked service behaves so.
        # Specific assertions depend on how `validate` is implemented in cli.py
        # If it calls a service method, mock_cli_chatcoder would need that method mocked.
        # As the provided cli.py snippet doesn't show a detailed validate impl,
        # we rely on the mock_cli_chatcoder fixture's default behavior or add specifics there.

    # --- 其他 CLI 命令测试可以类似添加 ---
    # ... (为其他 CLI 命令添加测试)
