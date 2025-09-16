# tests/test_full_cli.py
import unittest
from unittest.mock import patch, MagicMock, call, mock_open
from click.testing import CliRunner
import tempfile
import shutil
from pathlib import Path
import yaml
import json

# Import the CLI group
from chatcoder.cli import cli

class TestFullChatCoderCLI(unittest.TestCase):

    def setUp(self):
        """Set up test environment before each test method."""
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = Path.cwd()
        # Change to the temporary directory for the test
        import os
        os.chdir(self.test_dir)
        
        self.runner = CliRunner()
        self.chatcoder_dir = Path(".chatcoder")
        self.chatcoder_dir.mkdir()

        # Create mock config and context files
        self.config_data = {"test_config": "value1", "core_patterns": ["src/*.py"]}
        self.context_data = {"project_name": "MyProject", "custom_key": "custom_value"}
        with open(self.chatcoder_dir / "config.yaml", 'w') as f:
            yaml.dump(self.config_data, f)
        with open(self.chatcoder_dir / "context.yaml", 'w') as f:
            yaml.dump(self.context_data, f)
        
        # Ensure workflow_instances directory exists for Thinker instantiation
        (self.chatcoder_dir / "workflow_instances").mkdir()

    def tearDown(self):
        """Tear down test environment after each test method."""
        import os
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir, ignore_errors=True)

    # --- Helper Methods ---
    def _create_mock_thinker(self):
        """Helper to create a pre-configured mock Thinker instance."""
        mock_thinker = MagicMock()
        # Set up default return values for common methods
        mock_thinker.list_all_features.return_value = []
        mock_thinker.get_feature_instances.return_value = []
        mock_thinker.get_instance_detail_status.return_value = {}
        mock_thinker.delete_feature.return_value = True
        mock_thinker.get_active_instance_for_feature.return_value = "wfi_active_mock"
        return mock_thinker

    def _create_mock_coder(self):
        """Helper to create a pre-configured mock Coder instance."""
        mock_coder = MagicMock()
        mock_coder.apply_task.return_value = True # Default to success
        return mock_coder

    # --- Root CLI Group Tests ---
    def test_cli_no_command_shows_help(self):
        """Test that running `chatcoder` with no command shows help."""
        result = self.runner.invoke(cli)
        self.assertEqual(result.exit_code, 0)
        # Check for elements of the help message
        self.assertIn("Usage:", result.output)
        self.assertIn("Options:", result.output)
        self.assertIn("Commands:", result.output)

    def test_cli_version_option(self):
        """Test the --version option."""
        result = self.runner.invoke(cli, ['--version'])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("ChatCoder CLI v", result.output)

    # --- init command tests ---
    @patch('chatcoder.cli.perform_init_project')
    def test_init_command_success(self, mock_perform_init):
        """Test successful execution of the init command."""
        mock_perform_init.return_value = ("mock_config_content", "mock_context_content")
        
        # Delete existing files to trigger init logic
        (self.chatcoder_dir / "config.yaml").unlink()
        (self.chatcoder_dir / "context.yaml").unlink()

        result = self.runner.invoke(cli, ['init'], input='y\ny\n') # Simulate user 'y' confirms

        self.assertEqual(result.exit_code, 0)
        self.assertIn("项目初始化", result.output)
        self.assertIn("初始化完成！", result.output)
        # Verify files and directories are created
        self.assertTrue((self.chatcoder_dir / "config.yaml").exists())
        self.assertTrue((self.chatcoder_dir / "context.yaml").exists())
        self.assertTrue((self.chatcoder_dir / "workflow_instances").exists())

    # --- context command tests ---
    def test_context_command(self):
        """Test the context command displays raw config files."""
        result = self.runner.invoke(cli, ['context'])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("项目原始配置和上下文", result.output)
        self.assertIn("### config.yaml 内容:", result.output)
        self.assertIn("### context.yaml 内容:", result.output)
        # Check if JSON output contains key data (simple string check)
        self.assertIn("test_config", result.output)
        self.assertIn("project_name", result.output)

    # --- feature group tests ---
    @patch('chatcoder.cli.Thinker')
    def test_feature_start_command(self, mock_thinker_cls):
        """Test the feature start command."""
        mock_thinker = self._create_mock_thinker()
        mock_thinker_cls.return_value = mock_thinker
        mock_thinker.start_new_feature.return_value = {
            "feature_id": "feat_test",
            "description": "Test feature",
            "instance_id": "wfi_123"
        }

        result = self.runner.invoke(cli, ['feature', 'start', '-d', 'Test feature description'])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("🚀 Started new feature workflow: feat_test", result.output)
        mock_thinker_cls.assert_called_once()
        mock_thinker.start_new_feature.assert_called_once_with('Test feature description', 'default')

    @patch('chatcoder.cli.Thinker')
    def test_feature_list_command_empty(self, mock_thinker_cls):
        """Test the feature list command with no features."""
        mock_thinker = self._create_mock_thinker()
        mock_thinker_cls.return_value = mock_thinker
        mock_thinker.list_all_features.return_value = []

        result = self.runner.invoke(cli, ['feature', 'list'])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Features List", result.output)
        self.assertIn("No features found.", result.output)
        mock_thinker_cls.assert_called_once()
        mock_thinker.list_all_features.assert_called_once()

    @patch('chatcoder.cli.Thinker')
    def test_feature_list_command_with_features(self, mock_thinker_cls):
        """Test the feature list command with features."""
        mock_thinker = self._create_mock_thinker()
        mock_thinker_cls.return_value = mock_thinker
        mock_thinker.list_all_features.return_value = ['feat_1', 'feat_2']
        mock_thinker.get_feature_instances.side_effect = [
            [{"instance_id": "wfi_1"}], # For feat_1
            [{"instance_id": "wfi_2a"}, {"instance_id": "wfi_2b"}] # For feat_2
        ]

        result = self.runner.invoke(cli, ['feature', 'list'])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Features List", result.output)
        self.assertIn("feat_1", result.output)
        self.assertIn("1", result.output) # Instance count for feat_1
        self.assertIn("feat_2", result.output)
        self.assertIn("2", result.output) # Instance count for feat_2
        mock_thinker_cls.assert_called_once()
        mock_thinker.list_all_features.assert_called_once()
        self.assertEqual(mock_thinker.get_feature_instances.call_count, 2)

    @patch('chatcoder.cli.Thinker')
    def test_feature_status_command(self, mock_thinker_cls):
        """Test the feature status command."""
        mock_thinker = self._create_mock_thinker()
        mock_thinker_cls.return_value = mock_thinker
        mock_thinker.get_feature_instances.return_value = [
            {
                "instance_id": "wfi_abc123",
                "status": "running",
                "current_phase": "analyze",
                "progress": 0.5,
                "updated_at": 1700000000.0
            },
            {
                "instance_id": "wfi_def456",
                "status": "completed",
                "current_phase": "implement",
                "progress": 1.0,
                "updated_at": 1700000100.0
            }
        ]

        result = self.runner.invoke(cli, ['feature', 'status', 'feat_test'])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Instances for Feature: feat_test", result.output)
        self.assertIn("wfi_abc123", result.output)
        self.assertIn("running", result.output)
        self.assertIn("analyze", result.output)
        self.assertIn("50%", result.output)
        self.assertIn("wfi_def456", result.output)
        self.assertIn("completed", result.output)
        self.assertIn("implement", result.output)
        self.assertIn("100%", result.output)
        mock_thinker_cls.assert_called_once()
        mock_thinker.get_feature_instances.assert_called_once_with("feat_test")

    @patch('chatcoder.cli.Thinker')
    def test_feature_delete_command(self, mock_thinker_cls):
        """Test the feature delete command."""
        mock_thinker = self._create_mock_thinker()
        mock_thinker_cls.return_value = mock_thinker
        mock_thinker.delete_feature.return_value = True # Simulate successful deletion

        result = self.runner.invoke(cli, ['feature', 'delete', 'feat_to_delete'])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Feature 'feat_to_delete' and its instances have been deleted.", result.output)
        mock_thinker_cls.assert_called_once()
        mock_thinker.delete_feature.assert_called_once_with("feat_to_delete")

    # --- instance group tests ---
    @patch('chatcoder.cli.Thinker')
    def test_instance_status_command(self, mock_thinker_cls):
        """Test the instance status command."""
        mock_thinker = self._create_mock_thinker()
        mock_thinker_cls.return_value = mock_thinker
        mock_detail_status = {
            "instance_id": "wfi_xyz789",
            "feature_id": "feat_test",
            "current_phase": "design",
            "status": "running",
            "variables": {"key": "value"},
        }
        mock_thinker.get_instance_detail_status.return_value = mock_detail_status

        result = self.runner.invoke(cli, ['instance', 'status', 'wfi_xyz789'])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Instance Status: wfi_xyz789", result.output)
        # Check if JSON output contains key data
        self.assertIn('"instance_id": "wfi_xyz789"', result.output)
        self.assertIn('"feature_id": "feat_test"', result.output)
        mock_thinker_cls.assert_called_once()
        mock_thinker.get_instance_detail_status.assert_called_once_with("wfi_xyz789")

    # --- task group tests (direct instance_id usage) ---
    @patch('chatcoder.cli.Thinker')
    def test_task_prompt_with_id(self, mock_thinker_cls):
        """Test the task prompt command using --id."""
        mock_thinker = self._create_mock_thinker()
        mock_thinker_cls.return_value = mock_thinker
        mock_thinker.generate_prompt_for_current_task.return_value = "This is a test prompt for the task."

        result = self.runner.invoke(cli, ['task', 'prompt', '--id', 'wfi_test123'])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Generating prompt for instance: wfi_test123", result.output)
        self.assertIn("This is a test prompt for the task.", result.output)
        mock_thinker_cls.assert_called_once()
        mock_thinker.generate_prompt_for_current_task.assert_called_once_with("wfi_test123")

    @patch('chatcoder.cli.Thinker')
    def test_task_confirm_with_id(self, mock_thinker_cls):
        """Test the task confirm command using --id."""
        mock_thinker = self._create_mock_thinker()
        mock_thinker_cls.return_value = mock_thinker
        mock_thinker.confirm_task_and_advance.return_value = {
            "next_phase": "design",
            "status": "running",
            "feature_id": "feat_test"
        }

        result = self.runner.invoke(cli, ['task', 'confirm', '--id', 'wfi_test123', '--summary', 'Task done'])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("✅ Task for instance wfi_test123 has been confirmed.", result.output)
        self.assertIn("Next phase: design", result.output)
        mock_thinker_cls.assert_called_once()
        mock_thinker.confirm_task_and_advance.assert_called_once_with("wfi_test123", "Task done")

    @patch('chatcoder.cli.Thinker')
    def test_task_preview_with_id(self, mock_thinker_cls):
        """Test the task preview command using --id."""
        mock_thinker = self._create_mock_thinker()
        mock_thinker_cls.return_value = mock_thinker
        mock_thinker.preview_prompt_for_phase.return_value = "This is a preview prompt for phase X."

        result = self.runner.invoke(cli, ['task', 'preview', 'phase_x', '--id', 'wfi_test123'])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Previewing prompt for phase 'phase_x' of instance: wfi_test123", result.output)
        self.assertIn("This is a preview prompt for phase X.", result.output)
        mock_thinker_cls.assert_called_once()
        mock_thinker.preview_prompt_for_phase.assert_called_once_with("wfi_test123", "phase_x", "Preview task in phase 'phase_x'")

    @patch('chatcoder.cli.Thinker')
    @patch('chatcoder.cli.Coder')
    def test_task_apply_with_id(self, mock_coder_cls, mock_thinker_cls):
        """Test the task apply command using --id."""
        mock_thinker = self._create_mock_thinker()
        mock_thinker_cls.return_value = mock_thinker

        mock_coder = self._create_mock_coder()
        mock_coder_cls.return_value = mock_coder

        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as tf:
            tf.write("AI generated content for new_file.py")
            response_file_path = tf.name

        try:
            result = self.runner.invoke(cli, ['task', 'apply', '--id', 'wfi_test123', response_file_path])

            self.assertEqual(result.exit_code, 0)
            self.assertIn("Applying AI response for instance: wfi_test123", result.output)
            self.assertIn("AI response from", result.output) # Success message
            mock_thinker_cls.assert_called_once() # Ensure Thinker service was loaded
            mock_coder_cls.assert_called_once_with(mock_thinker) # Ensure Coder was created with Thinker
            mock_coder.apply_task.assert_called_once()
            called_args, called_kwargs = mock_coder.apply_task.call_args
            self.assertEqual(called_args[0], 'wfi_test123') # Check instance_id
            self.assertIn("AI generated content", called_args[1]) # Check content (partial match)

        finally:
            import os
            os.unlink(response_file_path) # Clean up temp file

    # --- task group tests (using --feature) ---
    @patch('chatcoder.cli.Thinker')
    def test_task_prompt_with_feature(self, mock_thinker_cls):
        """Test the task prompt command using --feature."""
        mock_thinker = self._create_mock_thinker()
        mock_thinker_cls.return_value = mock_thinker
        mock_thinker.get_active_instance_for_feature.return_value = "wfi_from_feature"
        mock_thinker.generate_prompt_for_current_task.return_value = "Prompt for active instance."

        result = self.runner.invoke(cli, ['task', 'prompt', '--feature', 'feat_test'])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Using active instance 'wfi_from_feature' for feature 'feat_test'", result.output)
        self.assertIn("Generating prompt for instance: wfi_from_feature", result.output)
        self.assertIn("Prompt for active instance.", result.output)
        mock_thinker_cls.assert_called_once()
        mock_thinker.get_active_instance_for_feature.assert_called_once_with("feat_test")
        mock_thinker.generate_prompt_for_current_task.assert_called_once_with("wfi_from_feature")

    @patch('chatcoder.cli.Thinker')
    def test_task_confirm_with_feature(self, mock_thinker_cls):
        """Test the task confirm command using --feature."""
        mock_thinker = self._create_mock_thinker()
        mock_thinker_cls.return_value = mock_thinker
        mock_thinker.get_active_instance_for_feature.return_value = "wfi_active"
        mock_thinker.confirm_task_and_advance.return_value = {
            "next_phase": "test",
            "status": "running",
            "feature_id": "feat_another"
        }

        result = self.runner.invoke(cli, ['task', 'confirm', '--feature', 'feat_another', '--summary', 'Work complete'])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Using active instance 'wfi_active' for feature 'feat_another'", result.output)
        self.assertIn("✅ Task for instance wfi_active has been confirmed.", result.output)
        self.assertIn("Next phase: test", result.output)
        mock_thinker_cls.assert_called_once()
        mock_thinker.get_active_instance_for_feature.assert_called_once_with("feat_another")
        mock_thinker.confirm_task_and_advance.assert_called_once_with("wfi_active", "Work complete")

    # --- feature task subgroup tests ---
    @patch('chatcoder.cli.Thinker')
    @patch('chatcoder.cli.Coder') # Also patch Coder for apply test within feature task
    def test_feature_task_commands(self, mock_coder_cls, mock_thinker_cls):
        """Test the feature task subgroup commands."""
        mock_thinker = self._create_mock_thinker()
        mock_thinker_cls.return_value = mock_thinker
        # Mock the resolution of feature_id to instance_id within the group setup
        mock_thinker.get_active_instance_for_feature.return_value = 'wfi_active456'

        mock_coder = self._create_mock_coder()
        mock_coder_cls.return_value = mock_coder

        # --- feature task status ---
        mock_thinker.get_instance_detail_status.return_value = {"instance_id": "wfi_active456", "status": "running"}
        result_status = self.runner.invoke(cli, ['feature', 'task', 'status', 'feat_test789'])
        self.assertEqual(result_status.exit_code, 0)
        self.assertIn("Active Task Instance Status for Feature 'feat_test789' (ID: wfi_active456)", result_status.output)
        mock_thinker.get_instance_detail_status.assert_called_with("wfi_active456")

        # Reset mock call count for next assertion
        mock_thinker.reset_mock()
        mock_thinker.get_active_instance_for_feature.return_value = 'wfi_active456' # Re-set

        # --- feature task prompt ---
        mock_thinker.generate_prompt_for_current_task.return_value = "Prompt for feature task."
        result_prompt = self.runner.invoke(cli, ['feature', 'task', 'prompt', 'feat_test789'])
        self.assertEqual(result_prompt.exit_code, 0)
        self.assertIn("Generating prompt for feature 'feat_test789' (active instance: wfi_active456)", result_prompt.output)
        mock_thinker.generate_prompt_for_current_task.assert_called_with("wfi_active456")

        # Reset mock call count for next assertion
        mock_thinker.reset_mock()
        mock_thinker.get_active_instance_for_feature.return_value = 'wfi_active456' # Re-set

        # --- feature task confirm ---
        mock_thinker.confirm_task_and_advance.return_value = {"next_phase": "deploy", "status": "running", "feature_id": "feat_test789"}
        result_confirm = self.runner.invoke(cli, ['feature', 'task', 'confirm', 'feat_test789', '--summary', 'Feature task done'])
        self.assertEqual(result_confirm.exit_code, 0)
        self.assertIn("✅ Task for instance wfi_active456 (feature 'feat_test789') has been confirmed.", result_confirm.output)
        mock_thinker.confirm_task_and_advance.assert_called_with("wfi_active456", "Feature task done")

        # Reset mock call count for next assertion
        mock_thinker.reset_mock()
        mock_thinker.get_active_instance_for_feature.return_value = 'wfi_active456' # Re-set

        # --- feature task preview ---
        mock_thinker.preview_prompt_for_phase.return_value = "Preview for feature task phase."
        result_preview = self.runner.invoke(cli, ['feature', 'task', 'preview', 'feat_test789', 'phase_y'])
        self.assertEqual(result_preview.exit_code, 0)
        self.assertIn("Previewing prompt for phase 'phase_y' of feature 'feat_test789' (instance: wfi_active456)", result_preview.output)
        mock_thinker.preview_prompt_for_phase.assert_called_with("wfi_active456", "phase_y", "Preview task in phase 'phase_y'")

        # Reset mock call count for next assertion
        mock_thinker.reset_mock()
        mock_thinker.get_active_instance_for_feature.return_value = 'wfi_active456' # Re-set
        mock_coder.reset_mock()

        # --- feature task apply ---
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as tf:
            tf.write("AI response for feature task.")
            response_file_path = tf.name

        try:
            result_apply = self.runner.invoke(cli, ['feature', 'task', 'apply', 'feat_test789', response_file_path])
            self.assertEqual(result_apply.exit_code, 0)
            self.assertIn("Applying AI response for feature 'feat_test789' (instance: wfi_active456)", result_apply.output)
            self.assertIn("AI response from", result_apply.output) # Success message
            mock_coder_cls.assert_called_once_with(mock_thinker)
            mock_coder.apply_task.assert_called_once()
            called_args, called_kwargs = mock_coder.apply_task.call_args
            self.assertEqual(called_args[0], 'wfi_active456')
            self.assertIn("AI response for feature task.", called_args[1])

        finally:
            import os
            os.unlink(response_file_path)

        # Ensure Thinker was called consistently for resolving the feature ID
        mock_thinker_cls.assert_called() # Called multiple times in this test
        # Check that get_active_instance_for_feature was called for each command
        self.assertEqual(mock_thinker.get_active_instance_for_feature.call_count, 5) # status, prompt, confirm, preview, apply


    # --- workflow group tests ---
    def test_workflow_list_command(self):
        """Test the workflow list command."""
        # Create mock workflow templates files
        workflows_dir = Path("ai-prompts") / "workflows"
        workflows_dir.mkdir(parents=True)
        (workflows_dir / "default.yaml").touch()
        (workflows_dir / "security_review.yaml").touch()
        (workflows_dir / "data_migration.json").touch() # Different extension

        result = self.runner.invoke(cli, ['workflow', 'list'])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Available Workflows", result.output)
        self.assertIn("default", result.output)
        self.assertIn("security_review", result.output)
        # .json file should not be listed if logic is correct
        self.assertNotIn("data_migration", result.output)

    # --- config validate command tests ---
    def test_config_validate_command(self):
        """Test the config validate command."""
        # This test assumes validate_config_content is a simple function that doesn't throw on valid YAML
        # A more thorough test would mock validate_config_content
        result = self.runner.invoke(cli, ['validate'])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("配置文件验证通过！", result.output)

    # --- Error Handling Tests ---
    def test_missing_config_files_error(self):
        """Test CLI command error handling when config files are missing."""
        # Delete config files
        (self.chatcoder_dir / "config.yaml").unlink()
        (self.chatcoder_dir / "context.yaml").unlink()
        
        # Try running a command that needs Thinker service
        result = self.runner.invoke(cli, ['feature', 'list'])
        
        self.assertNotEqual(result.exit_code, 0) # Should exit with error
        self.assertIn("配置文件缺失", result.output)
        self.assertIn("请先运行 `chatcoder init`", result.output)

    @patch('chatcoder.cli.Thinker')
    def test_thinker_initialization_error(self, mock_thinker_cls):
        """Test error handling if Thinker fails to initialize."""
        mock_thinker_cls.side_effect = Exception("Thinker init failed")

        result = self.runner.invoke(cli, ['feature', 'list']) # Any command needing Thinker

        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("❌", result.output) # Error indicator from console.error
        self.assertIn("Thinker init failed", result.output)

    @patch('chatcoder.cli.Thinker')
    def test_task_apply_missing_response_file(self, mock_thinker_cls):
        """Test task apply with a non-existent response file."""
        mock_thinker = self._create_mock_thinker()
        mock_thinker_cls.return_value = mock_thinker

        result = self.runner.invoke(cli, ['task', 'apply', '--id', 'wfi_test', '/path/does/not/exist.txt'])

        self.assertNotEqual(result.exit_code, 0) # Should exit with error
        self.assertIn("❌", result.output) # Error indicator
        self.assertIn("AI response file not found", result.output)


if __name__ == '__main__':
    unittest.main()
