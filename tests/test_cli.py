# tests/test_cli.py
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

class TestChatCoderCLI(unittest.TestCase):

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

    def tearDown(self):
        """Tear down test environment after each test method."""
        import os
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir, ignore_errors=True)

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

    # --- feature start command tests ---
    @patch('chatcoder.cli.Thinker') # Patch the Thinker class itself
    def test_feature_start_command(self, mock_thinker_cls):
        """Test the feature start command."""
        mock_thinker = MagicMock()
        mock_thinker_cls.return_value = mock_thinker
        mock_thinker.start_new_feature.return_value = {
            "feature_id": "feat_test",
            "description": "Test feature",
            "instance_id": "wfi_123"
        }

        result = self.runner.invoke(cli, ['feature', 'start', '-d', 'Test feature description'])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("🚀 Started new feature workflow: feat_test", result.output)
        mock_thinker_cls.assert_called_once() # Check Thinker was instantiated
        mock_thinker.start_new_feature.assert_called_once_with('Test feature description', 'default') # Check method call

    # --- feature list command tests ---
    @patch('chatcoder.cli.Thinker')
    def test_feature_list_command(self, mock_thinker_cls):
        """Test the feature list command."""
        mock_thinker = MagicMock()
        mock_thinker_cls.return_value = mock_thinker
        mock_thinker.list_all_features.return_value = ['feat_1', 'feat_2']
        # Mock get_feature_instances for counts if needed in the test
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
        mock_thinker.get_feature_instances.assert_any_call("feat_1")
        mock_thinker.get_feature_instances.assert_any_call("feat_2")

    # --- feature status command tests ---
    @patch('chatcoder.cli.Thinker')
    def test_feature_status_command(self, mock_thinker_cls):
        """Test the feature status command."""
        mock_thinker = MagicMock()
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

    # --- feature delete command tests ---
    @patch('chatcoder.cli.Thinker')
    def test_feature_delete_command(self, mock_thinker_cls):
        """Test the feature delete command."""
        mock_thinker = MagicMock()
        mock_thinker_cls.return_value = mock_thinker
        mock_thinker.delete_feature.return_value = True

        result = self.runner.invoke(cli, ['feature', 'delete', 'feat_to_delete'])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Feature 'feat_to_delete' and its instances have been deleted.", result.output)
        mock_thinker_cls.assert_called_once()
        mock_thinker.delete_feature.assert_called_once_with("feat_to_delete")

    # --- task apply command tests (using --id) ---
    @patch('chatcoder.cli.Thinker')
    def test_task_apply_command_with_id(self, mock_thinker_cls):
        """Test the task apply command using --id."""
        # Setup mocks
        mock_thinker = MagicMock()
        mock_thinker_cls.return_value = mock_thinker

        mock_coder_constructor = MagicMock()
        mock_coder_instance = MagicMock()
        mock_coder_instance.apply_task.return_value = True # Simulate success
        mock_coder_constructor.return_value = mock_coder_instance

        # Create a temporary file for the AI response
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as tf:
            tf.write("AI generated content for new_file.py")
            response_file_path = tf.name

        try:
            # Patch Coder within the test context
            with patch('chatcoder.cli.Coder', mock_coder_constructor):
                result = self.runner.invoke(cli, ['task', 'apply', '--id', 'wfi_test123', response_file_path])

            self.assertEqual(result.exit_code, 0)
            self.assertIn("AI response from", result.output) # Check for success message
            mock_thinker_cls.assert_called_once() # Ensure Thinker service was loaded
            mock_coder_constructor.assert_called_once_with(mock_thinker) # Ensure Coder was created with Thinker
            # Check that the response file content was read and passed
            mock_coder_instance.apply_task.assert_called_once()
            called_args, called_kwargs = mock_coder_instance.apply_task.call_args
            self.assertEqual(called_args[0], 'wfi_test123') # Check instance_id
            self.assertIn("AI generated content", called_args[1]) # Check content (partial match)

        finally:
            import os
            os.unlink(response_file_path) # Clean up temp file

    # --- feature task apply command tests ---
    @patch('chatcoder.cli.Thinker')
    def test_feature_task_apply_command(self, mock_thinker_cls):
        """Test the feature task apply command."""
        # Setup mocks for Thinker and Coder interaction within feature group
        mock_thinker = MagicMock()
        mock_thinker_cls.return_value = mock_thinker
        # Mock the resolution of feature_id to instance_id
        mock_thinker.get_active_instance_for_feature.return_value = 'wfi_active456'

        mock_coder_constructor = MagicMock()
        mock_coder_instance = MagicMock()
        mock_coder_instance.apply_task.return_value = True # Simulate success
        mock_coder_constructor.return_value = mock_coder_instance

        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as tf:
            tf.write("AI generated content for feature_file.py")
            response_file_path = tf.name

        try:
            # Patch Coder within the test context
            with patch('chatcoder.cli.Coder', mock_coder_constructor):
                # Invoke the feature task apply command
                result = self.runner.invoke(cli, ['feature', 'task', 'apply', 'feat_test789', response_file_path])

            self.assertEqual(result.exit_code, 0)
            self.assertIn("AI response from", result.output) # Check for success message
            mock_thinker_cls.assert_called_once()
            # Check that feature ID was resolved to instance ID
            mock_thinker.get_active_instance_for_feature.assert_called_once_with('feat_test789')
            mock_coder_constructor.assert_called_once_with(mock_thinker)
            # Check that Coder.apply_task was called with the resolved instance_id
            mock_coder_instance.apply_task.assert_called_once()
            called_args, called_kwargs = mock_coder_instance.apply_task.call_args
            self.assertEqual(called_args[0], 'wfi_active456') # Check resolved instance_id
            self.assertIn("AI generated content", called_args[1]) # Check content (partial match)

        finally:
            import os
            os.unlink(response_file_path)

    # --- workflow list command tests ---
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

    # --- Missing config files error handling ---
    def test_missing_config_files_error(self):
        """Test CLI command error handling when config files are missing."""
        # Delete config files
        (self.chatcoder_dir / "config.yaml").unlink()
        (self.chatcoder_dir / "context.yaml").unlink()
        
        # Try running a command that needs ChatCoder service
        result = self.runner.invoke(cli, ['feature', 'list'])
        
        self.assertNotEqual(result.exit_code, 0) # Should exit with error
        self.assertIn("配置文件缺失", result.output)
        self.assertIn("请先运行 `chatcoder init`", result.output)

if __name__ == '__main__':
    unittest.main()
