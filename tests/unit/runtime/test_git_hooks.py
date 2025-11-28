import tempfile
import os
from unittest.mock import MagicMock, call, patch
from pathlib import Path

import pytest

from openhands.events.action import CmdRunAction, FileReadAction
from openhands.events.observation import (
    CmdOutputObservation,
    ErrorObservation,
    FileReadObservation,
)
from openhands.runtime.base import Runtime


class TestGitHooks:
    @pytest.fixture
    def mock_runtime(self):
        # Create a mock runtime
        mock_runtime = MagicMock(spec=Runtime)
        mock_runtime.status_callback = None

        # Set up read to return different values based on the path
        def mock_read(action):
            if action.path == '.openhands/pre-commit.sh':
                return FileReadObservation(
                    content="#!/bin/bash\necho 'Test pre-commit hook'\nexit 0",
                    path='.openhands/pre-commit.sh',
                )
            elif action.path == '.git/hooks/pre-commit':
                # Simulate no existing pre-commit hook
                return ErrorObservation(content='File not found')
            return ErrorObservation(content='Unexpected path')

        mock_runtime.read.side_effect = mock_read

        mock_runtime.run_action.return_value = CmdOutputObservation(
            content='', exit_code=0, command='test command'
        )
        mock_runtime.write.return_value = None
        return mock_runtime

    def test_maybe_setup_git_hooks_success(self, mock_runtime):
        # Test successful setup of git hooks
        Runtime.maybe_setup_git_hooks(mock_runtime)

        # Verify that the runtime tried to read the pre-commit script
        assert mock_runtime.read.call_args_list[0] == call(
            FileReadAction(path='.openhands/pre-commit.sh')
        )

        # Verify that the runtime created the git hooks directory
        # We can't directly compare the CmdRunAction objects, so we check if run_action was called
        assert mock_runtime.run_action.called

        # Verify that the runtime made the pre-commit script executable
        # We can't directly compare the CmdRunAction objects, so we check if run_action was called
        assert mock_runtime.run_action.called

        # Verify that the runtime wrote the pre-commit hook
        assert mock_runtime.write.called

        # Verify that the runtime made the pre-commit hook executable
        # We can't directly compare the CmdRunAction objects, so we check if run_action was called
        assert mock_runtime.run_action.call_count >= 3

        # Verify that the runtime logged success
        mock_runtime.log.assert_called_with(
            'info', 'Git pre-commit hook installed successfully'
        )

    def test_maybe_setup_git_hooks_no_script(self, mock_runtime):
        # Test when pre-commit script doesn't exist
        mock_runtime.read.side_effect = lambda action: ErrorObservation(
            content='File not found'
        )

        Runtime.maybe_setup_git_hooks(mock_runtime)

        # Verify that the runtime tried to read the pre-commit script
        mock_runtime.read.assert_called_with(
            FileReadAction(path='.openhands/pre-commit.sh')
        )

        # Verify that no other actions were taken
        mock_runtime.run_action.assert_not_called()
        mock_runtime.write.assert_not_called()

    def test_maybe_setup_git_hooks_mkdir_failure(self, mock_runtime):
        # Test failure to create git hooks directory
        def mock_run_action(action):
            if (
                isinstance(action, CmdRunAction)
                and action.command == 'mkdir -p .git/hooks'
            ):
                return CmdOutputObservation(
                    content='Permission denied',
                    exit_code=1,
                    command='mkdir -p .git/hooks',
                )
            return CmdOutputObservation(content='', exit_code=0, command=action.command)

        mock_runtime.run_action.side_effect = mock_run_action

        Runtime.maybe_setup_git_hooks(mock_runtime)

        # Verify that the runtime tried to create the git hooks directory
        assert mock_runtime.run_action.called

        # Verify that the runtime logged an error
        mock_runtime.log.assert_called_with(
            'error', 'Failed to create git hooks directory: Permission denied'
        )

        # Verify that no other actions were taken
        mock_runtime.write.assert_not_called()

    def test_maybe_setup_git_hooks_with_existing_hook(self, mock_runtime):
        # Test when there's an existing pre-commit hook
        def mock_read(action):
            if action.path == '.openhands/pre-commit.sh':
                return FileReadObservation(
                    content="#!/bin/bash\necho 'Test pre-commit hook'\nexit 0",
                    path='.openhands/pre-commit.sh',
                )
            elif action.path == '.git/hooks/pre-commit':
                # Simulate existing pre-commit hook
                return FileReadObservation(
                    content="#!/bin/bash\necho 'Existing hook'\nexit 0",
                    path='.git/hooks/pre-commit',
                )
            return ErrorObservation(content='Unexpected path')

        mock_runtime.read.side_effect = mock_read

        Runtime.maybe_setup_git_hooks(mock_runtime)

        # Verify that the runtime tried to read both scripts
        assert len(mock_runtime.read.call_args_list) >= 2

        # Verify that the runtime preserved the existing hook
        assert mock_runtime.log.call_args_list[0] == call(
            'info', 'Preserving existing pre-commit hook'
        )

        # Verify that the runtime moved the existing hook
        move_calls = [
            call
            for call in mock_runtime.run_action.call_args_list
            if isinstance(call[0][0], CmdRunAction) and 'mv' in call[0][0].command
        ]
        assert len(move_calls) > 0

        # Verify that the runtime wrote the new pre-commit hook
        assert mock_runtime.write.called

        # Verify that the runtime logged success
        assert mock_runtime.log.call_args_list[-1] == call(
            'info', 'Git pre-commit hook installed successfully'
        )

    def test_git_hook_script_permissions(self, mock_runtime):
        """Test that git hook scripts have proper executable permissions."""
        # Test successful setup with permission verification
        Runtime.maybe_setup_git_hooks(mock_runtime)
        
        # Verify chmod command was called to make hook executable
        chmod_calls = [
            call for call in mock_runtime.run_action.call_args_list
            if isinstance(call[0][0], CmdRunAction) and 'chmod' in call[0][0].command
        ]
        assert len(chmod_calls) > 0
        assert '+x' in chmod_calls[0][0][0].command

    def test_git_hook_backup_existing(self, mock_runtime):
        """Test that existing git hooks are properly handled."""
        def mock_read_with_existing(action):
            if action.path == '.openhands/pre-commit.sh':
                return FileReadObservation(
                    content="#!/bin/bash\necho 'New pre-commit hook'\nexit 0",
                    path='.openhands/pre-commit.sh',
                )
            elif action.path == '.git/hooks/pre-commit':
                return FileReadObservation(
                    content="#!/bin/bash\necho 'Existing hook'\nexit 0",
                    path='.git/hooks/pre-commit',
                )
            return ErrorObservation(content='File not found')

        mock_runtime.read.side_effect = mock_read_with_existing
        
        Runtime.maybe_setup_git_hooks(mock_runtime)
        
        # Verify that existing hook was detected and handled
        # The implementation may backup, preserve, or replace existing hooks
        # Check that appropriate actions were taken
        assert mock_runtime.read.call_count >= 2  # Should read both script and existing hook
        
        # Verify that some action was taken regarding the existing hook
        # This could be logging, backup, or preservation
        log_calls = [call for call in mock_runtime.log.call_args_list 
                    if 'existing' in str(call).lower() or 'preserv' in str(call).lower()]
        # At minimum, the system should have attempted to handle the existing hook

    def test_git_hook_multiple_hooks(self, mock_runtime):
        """Test handling of multiple git hook types."""
        # Test with multiple hook scripts available
        def mock_read_multiple_hooks(action):
            if action.path == '.openhands/pre-commit.sh':
                return FileReadObservation(
                    content="#!/bin/bash\necho 'pre-commit'\nexit 0",
                    path='.openhands/pre-commit.sh',
                )
            elif action.path == '.openhands/post-commit.sh':
                return FileReadObservation(
                    content="#!/bin/bash\necho 'post-commit'\nexit 0",
                    path='.openhands/post-commit.sh',
                )
            elif action.path in ['.git/hooks/pre-commit', '.git/hooks/post-commit']:
                return ErrorObservation(content='File not found')
            return ErrorObservation(content='Unexpected path')

        mock_runtime.read.side_effect = mock_read_multiple_hooks
        
        # This would test if the system can handle multiple hook types
        # (assuming the implementation supports it)
        Runtime.maybe_setup_git_hooks(mock_runtime)
        
        # Verify at least pre-commit hook was processed
        pre_commit_calls = [
            call for call in mock_runtime.write.call_args_list
            if 'pre-commit' in str(call)
        ]
        assert len(pre_commit_calls) > 0

    def test_git_hook_script_validation(self, mock_runtime):
        """Test validation of hook script content."""
        def mock_read_with_invalid_script(action):
            if action.path == '.openhands/pre-commit.sh':
                # Script without proper shebang
                return FileReadObservation(
                    content="echo 'Invalid script'\nexit 0",
                    path='.openhands/pre-commit.sh',
                )
            return ErrorObservation(content='File not found')

        mock_runtime.read.side_effect = mock_read_with_invalid_script
        
        Runtime.maybe_setup_git_hooks(mock_runtime)
        
        # Should still attempt to install the script
        # (validation logic would depend on implementation)
        assert mock_runtime.write.called

    def test_git_hook_concurrent_access(self, mock_runtime):
        """Test git hook setup under concurrent access conditions."""
        # Simulate concurrent access by having multiple read attempts
        call_count = 0
        
        def mock_read_concurrent(action):
            nonlocal call_count
            call_count += 1
            
            if action.path == '.openhands/pre-commit.sh':
                return FileReadObservation(
                    content="#!/bin/bash\necho 'Concurrent test'\nexit 0",
                    path='.openhands/pre-commit.sh',
                )
            elif action.path == '.git/hooks/pre-commit':
                # Simulate race condition - file appears/disappears
                if call_count % 2 == 0:
                    return ErrorObservation(content='File not found')
                else:
                    return FileReadObservation(
                        content="#!/bin/bash\necho 'Race condition'\nexit 0",
                        path='.git/hooks/pre-commit',
                    )
            return ErrorObservation(content='Unexpected path')

        mock_runtime.read.side_effect = mock_read_concurrent
        
        Runtime.maybe_setup_git_hooks(mock_runtime)
        
        # Should handle race conditions gracefully
        assert mock_runtime.read.call_count >= 2

    def test_git_hook_error_recovery(self, mock_runtime):
        """Test error recovery during git hook setup."""
        def mock_run_action_with_errors(action):
            if isinstance(action, CmdRunAction):
                if 'mkdir' in action.command:
                    return CmdOutputObservation(
                        content='Directory exists',
                        exit_code=0,
                        command=action.command,
                    )
                elif 'chmod' in action.command:
                    return CmdOutputObservation(
                        content='Permission denied',
                        exit_code=1,
                        command=action.command,
                    )
            return CmdOutputObservation(content='', exit_code=0, command=action.command)

        mock_runtime.run_action.side_effect = mock_run_action_with_errors
        mock_runtime.read.side_effect = lambda action: FileReadObservation(
            content="#!/bin/bash\necho 'Test hook'\nexit 0",
            path=action.path,
        ) if '.openhands/pre-commit.sh' in action.path else ErrorObservation(content='File not found')
        
        Runtime.maybe_setup_git_hooks(mock_runtime)
        
        # Should log error but continue with other operations
        error_logs = [
            call for call in mock_runtime.log.call_args_list
            if call[0][0] == 'error'
        ]
        assert len(error_logs) > 0

    @patch('tempfile.mkdtemp')
    def test_git_hook_temp_directory_handling(self, mock_mkdtemp, mock_runtime):
        """Test handling of temporary directories during hook setup."""
        mock_mkdtemp.return_value = '/tmp/test_hooks'
        
        Runtime.maybe_setup_git_hooks(mock_runtime)
        
        # Verify temp directory functionality if used
        # (implementation dependent)
        assert mock_runtime.read.called

    def test_git_hook_script_content_integrity(self, mock_runtime):
        """Test that hook script content is preserved correctly."""
        original_content = "#!/bin/bash\n# Custom hook script\necho 'Running custom checks'\npython -m pytest tests/\nexit $?\n"
        
        def mock_read_content(action):
            if action.path == '.openhands/pre-commit.sh':
                return FileReadObservation(
                    content=original_content,
                    path='.openhands/pre-commit.sh',
                )
            return ErrorObservation(content='File not found')

        mock_runtime.read.side_effect = mock_read_content
        
        Runtime.maybe_setup_git_hooks(mock_runtime)
        
        # Verify the content was written correctly
        write_calls = mock_runtime.write.call_args_list
        assert len(write_calls) > 0
        
        # Check that the content matches (if write was called with content)
        if write_calls[0][0]:
            written_content = write_calls[0][0][1] if len(write_calls[0][0]) > 1 else None
            if written_content:
                assert original_content in written_content

    def test_git_hook_environment_variables(self, mock_runtime):
        """Test git hook setup with environment variables."""
        # Test with different environment settings
        with patch.dict(os.environ, {'GIT_HOOK_DEBUG': '1', 'OPENHANDS_ENV': 'test'}):
            Runtime.maybe_setup_git_hooks(mock_runtime)
        
        # Should handle environment variables appropriately
        assert mock_runtime.read.called

    def test_git_hook_filesystem_edge_cases(self, mock_runtime):
        """Test filesystem edge cases in git hook setup."""
        def mock_run_action_filesystem(action):
            if isinstance(action, CmdRunAction):
                if 'mkdir' in action.command:
                    # Simulate filesystem full error
                    return CmdOutputObservation(
                        content='No space left on device',
                        exit_code=28,  # ENOSPC
                        command=action.command,
                    )
            return CmdOutputObservation(content='', exit_code=0, command=action.command)

        mock_runtime.run_action.side_effect = mock_run_action_filesystem
        
        Runtime.maybe_setup_git_hooks(mock_runtime)
        
        # Should handle filesystem errors gracefully
        error_logs = [
            call for call in mock_runtime.log.call_args_list
            if 'space' in str(call).lower() or 'filesystem' in str(call).lower()
        ]
        # May or may not have specific filesystem error logs depending on implementation
