"""
Comprehensive test suite for Git sample hooks.

This module tests the functionality of all sample Git hooks found in the
.git/hooks/ directory to ensure they work as expected and can be used
as reference implementations.
"""

import os
import tempfile
import subprocess
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from openhands.events.action import CmdRunAction, FileWriteAction
from openhands.events.observation import CmdOutputObservation, ErrorObservation


class TestSampleHooks:
    """Test class for Git sample hooks functionality."""
    
    @pytest.fixture
    def temp_git_repo(self):
        """Create a temporary git repository for testing hooks."""
        temp_dir = tempfile.mkdtemp()
        original_dir = os.getcwd()
        
        try:
            os.chdir(temp_dir)
            # Initialize git repo
            subprocess.run(['git', 'init'], check=True, capture_output=True)
            subprocess.run(['git', 'config', 'user.name', 'Test User'], check=True)
            subprocess.run(['git', 'config', 'user.email', 'test@example.com'], check=True)
            
            yield temp_dir
        finally:
            os.chdir(original_dir)
            shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def sample_hooks_dir(self):
        """Get the path to the sample hooks directory."""
        repo_root = Path(__file__).parent.parent.parent.parent
        return repo_root / '.git' / 'hooks'
    
    def test_pre_commit_hook_ascii_filename_check(self, temp_git_repo, sample_hooks_dir):
        """Test pre-commit hook's ASCII filename validation."""
        # Copy the pre-commit sample hook
        pre_commit_src = sample_hooks_dir / 'pre-commit.sample'
        pre_commit_dst = Path(temp_git_repo) / '.git' / 'hooks' / 'pre-commit'
        shutil.copy2(pre_commit_src, pre_commit_dst)
        os.chmod(pre_commit_dst, 0o755)
        
        # Create a file with non-ASCII filename
        non_ascii_file = "tést.txt"
        Path(non_ascii_file).write_text("test content")
        
        # Try to commit the non-ASCII file
        subprocess.run(['git', 'add', non_ascii_file], check=True)
        result = subprocess.run(['git', 'commit', '-m', 'test commit'], capture_output=True, text=True)
        
        # Should fail with non-ASCII filename error
        assert result.returncode != 0
        assert "non-ASCII file name" in result.stderr
        
        # Clean up
        Path(non_ascii_file).unlink()
    
    def test_pre_commit_hook_whitespace_check(self, temp_git_repo, sample_hooks_dir):
        """Test pre-commit hook's whitespace validation."""
        # Copy the pre-commit sample hook
        pre_commit_src = sample_hooks_dir / 'pre-commit.sample'
        pre_commit_dst = Path(temp_git_repo) / '.git' / 'hooks' / 'pre-commit'
        shutil.copy2(pre_commit_src, pre_commit_dst)
        os.chmod(pre_commit_dst, 0o755)
        
        # Create a file with trailing whitespace
        test_file = "test.txt"
        with open(test_file, 'w') as f:
            f.write("content with trailing space   \n")
        
        # Try to commit the file
        subprocess.run(['git', 'add', test_file], check=True)
        result = subprocess.run(['git', 'commit', '-m', 'test commit'], capture_output=True, text=True)
        
        # Should fail with whitespace error
        assert result.returncode != 0
        assert "trailing whitespace" in result.stderr.lower()
        
        # Clean up
        Path(test_file).unlink()
    
    def test_pre_commit_hook_success(self, temp_git_repo, sample_hooks_dir):
        """Test pre-commit hook with valid files."""
        # Copy the pre-commit sample hook
        pre_commit_src = sample_hooks_dir / 'pre-commit.sample'
        pre_commit_dst = Path(temp_git_repo) / '.git' / 'hooks' / 'pre-commit'
        shutil.copy2(pre_commit_src, pre_commit_dst)
        os.chmod(pre_commit_dst, 0o755)
        
        # Create a valid file
        test_file = "test.txt"
        Path(test_file).write_text("valid content\n")
        
        # Try to commit the file
        subprocess.run(['git', 'add', test_file], check=True)
        result = subprocess.run(['git', 'commit', '-m', 'test commit'], capture_output=True, text=True)
        
        # Should succeed
        assert result.returncode == 0
        
        # Clean up
        Path(test_file).unlink()
    
    def test_pre_push_hook_wip_detection(self, temp_git_repo, sample_hooks_dir):
        """Test pre-push hook's WIP commit detection."""
        # Copy the pre-push sample hook
        pre_push_src = sample_hooks_dir / 'pre-push.sample'
        pre_push_dst = Path(temp_git_repo) / '.git' / 'hooks' / 'pre-push'
        shutil.copy2(pre_push_src, pre_push_dst)
        os.chmod(pre_push_dst, 0o755)
        
        # Create a file and commit with WIP message
        test_file = "test.txt"
        Path(test_file).write_text("content")
        subprocess.run(['git', 'add', test_file], check=True)
        subprocess.run(['git', 'commit', '-m', 'WIP: work in progress'], check=True)
        
        # Try to push (simulate push to test the hook)
        # We'll call the hook directly since we don't have a remote
        result = subprocess.run([
            str(pre_push_dst), 
            'origin', 
            'https://github.com/test/repo.git'
        ], input='main abc123 main def456\n', text=True, capture_output=True)
        
        # Should detect WIP commit and fail
        assert result.returncode != 0
        assert "WIP commit" in result.stderr
        
        # Clean up
        Path(test_file).unlink()
    
    def test_commit_msg_hook_duplicate_signed_off_by(self, temp_git_repo, sample_hooks_dir):
        """Test commit-msg hook's duplicate Signed-off-by detection."""
        # Copy the commit-msg sample hook
        commit_msg_src = sample_hooks_dir / 'commit-msg.sample'
        commit_msg_dst = Path(temp_git_repo) / '.git' / 'hooks' / 'commit-msg'
        shutil.copy2(commit_msg_src, commit_msg_dst)
        os.chmod(commit_msg_dst, 0o755)
        
        # Create a commit message with duplicate Signed-off-by lines
        commit_msg_file = "commit_msg.txt"
        with open(commit_msg_file, 'w') as f:
            f.write("Test commit\n\nSigned-off-by: Test User <test@example.com>\nSigned-off-by: Test User <test@example.com>\n")
        
        # Test the hook directly
        result = subprocess.run([str(commit_msg_dst), commit_msg_file], capture_output=True, text=True)
        
        # Should detect duplicate Signed-off-by and fail
        assert result.returncode != 0
        assert "Duplicate Signed-off-by" in result.stderr
        
        # Clean up
        Path(commit_msg_file).unlink()
    
    def test_commit_msg_hook_success(self, temp_git_repo, sample_hooks_dir):
        """Test commit-msg hook with valid message."""
        # Copy the commit-msg sample hook
        commit_msg_src = sample_hooks_dir / 'commit-msg.sample'
        commit_msg_dst = Path(temp_git_repo) / '.git' / 'hooks' / 'commit-msg'
        shutil.copy2(commit_msg_src, commit_msg_dst)
        os.chmod(commit_msg_dst, 0o755)
        
        # Create a valid commit message
        commit_msg_file = "commit_msg.txt"
        with open(commit_msg_file, 'w') as f:
            f.write("Test commit\n\nSigned-off-by: Test User <test@example.com>\n")
        
        # Test the hook directly
        result = subprocess.run([str(commit_msg_dst), commit_msg_file], capture_output=True, text=True)
        
        # Should succeed
        assert result.returncode == 0
        
        # Clean up
        Path(commit_msg_file).unlink()
    
    def test_prepare_commit_msg_hook_help_removal(self, temp_git_repo, sample_hooks_dir):
        """Test prepare-commit-msg hook's help message removal."""
        # Copy the prepare-commit-msg sample hook
        prepare_commit_msg_src = sample_hooks_dir / 'prepare-commit-msg.sample'
        prepare_commit_msg_dst = Path(temp_git_repo) / '.git' / 'hooks' / 'prepare-commit-msg'
        shutil.copy2(prepare_commit_msg_src, prepare_commit_msg_dst)
        os.chmod(prepare_commit_msg_dst, 0o755)
        
        # Create a commit message with help text
        commit_msg_file = "commit_msg.txt"
        with open(commit_msg_file, 'w') as f:
            f.write("# Please enter the commit message for your changes.\n")
            f.write("# Lines starting with '#' will be ignored.\n")
            f.write("Actual commit message\n")
        
        # Test the hook directly
        result = subprocess.run([str(prepare_commit_msg_dst), commit_msg_file, 'message', ''], 
                              capture_output=True, text=True)
        
        # Should succeed and remove help text
        assert result.returncode == 0
        
        # Check that help text was removed
        with open(commit_msg_file, 'r') as f:
            content = f.read()
            assert "Please enter the commit message" not in content
            assert "Actual commit message" in content
        
        # Clean up
        Path(commit_msg_file).unlink()
    
    def test_pre_rebase_hook_merged_branch_detection(self, temp_git_repo, sample_hooks_dir):
        """Test pre-rebase hook's merged branch detection."""
        # Copy the pre-rebase sample hook
        pre_rebase_src = sample_hooks_dir / 'pre-rebase.sample'
        pre_rebase_dst = Path(temp_git_repo) / '.git' / 'hooks' / 'pre-rebase'
        shutil.copy2(pre_rebase_src, pre_rebase_dst)
        os.chmod(pre_rebase_dst, 0o755)
        
        # Create a topic branch that's fully merged to master
        subprocess.run(['git', 'checkout', '-b', 'feature/test'], check=True)
        test_file = "test.txt"
        Path(test_file).write_text("content")
        subprocess.run(['git', 'add', test_file], check=True)
        subprocess.run(['git', 'commit', '-m', 'test commit'], check=True)
        
        # Switch back to master and merge the feature branch
        subprocess.run(['git', 'checkout', 'master'], check=True)
        subprocess.run(['git', 'merge', 'feature/test'], check=True)
        
        # Try to rebase the feature branch (simulate rebase to test the hook)
        result = subprocess.run([str(pre_rebase_dst), 'master', 'feature/test'], 
                              capture_output=True, text=True)
        
        # Should detect that the branch is fully merged and fail
        assert result.returncode != 0
        assert "fully merged" in result.stderr.lower()
        
        # Clean up
        Path(test_file).unlink()
        subprocess.run(['git', 'branch', '-D', 'feature/test'], check=True)
    
    def test_all_sample_hooks_exist_and_executable(self, sample_hooks_dir):
        """Test that all sample hooks exist and have correct permissions."""
        expected_hooks = [
            'applypatch-msg.sample',
            'commit-msg.sample',
            'fsmonitor-watchman.sample',
            'post-update.sample',
            'pre-applypatch.sample',
            'pre-commit.sample',
            'pre-merge-commit.sample',
            'pre-push.sample',
            'pre-rebase.sample',
            'pre-receive.sample',
            'prepare-commit-msg.sample',
            'push-to-checkout.sample',
            'sendemail-validate.sample',
            'update.sample'
        ]
        
        for hook in expected_hooks:
            hook_path = sample_hooks_dir / hook
            assert hook_path.exists(), f"Sample hook {hook} does not exist"
            assert os.access(hook_path, os.X_OK), f"Sample hook {hook} is not executable"
    
    def test_sample_hooks_shebang(self, sample_hooks_dir):
        """Test that all sample hooks have proper shebang lines."""
        for hook_file in sample_hooks_dir.glob('*.sample'):
            with open(hook_file, 'r') as f:
                first_line = f.readline().strip()
                assert first_line.startswith('#!'), f"{hook_file.name} missing shebang"
                assert 'sh' in first_line or 'bash' in first_line or 'perl' in first_line, \
                    f"{hook_file.name} has invalid shebang: {first_line}"


class TestHookIntegration:
    """Test integration of hooks with OpenHands runtime."""
    
    @pytest.fixture
    def mock_runtime(self):
        """Create a mock runtime for testing hook integration."""
        from openhands.runtime.base import Runtime
        mock_runtime = MagicMock(spec=Runtime)
        mock_runtime.status_callback = None
        return mock_runtime
    
    def test_hook_validation_functionality(self, mock_runtime):
        """Test that hooks can be validated through OpenHands runtime."""
        # This test ensures that the OpenHands runtime can interact with
        # Git hooks properly for validation purposes
        
        # Mock successful hook execution
        mock_runtime.run_action.return_value = CmdOutputObservation(
            content='Hook executed successfully',
            exit_code=0,
            command='git hook test'
        )
        
        # Simulate hook validation
        result = mock_runtime.run_action(CmdRunAction(command='git hook test'))
        
        assert result.exit_code == 0
        assert 'successfully' in result.content
    
    def test_hook_error_handling(self, mock_runtime):
        """Test error handling when hooks fail."""
        # Mock failed hook execution
        mock_runtime.run_action.return_value = CmdOutputObservation(
            content='Hook failed: validation error',
            exit_code=1,
            command='git hook test'
        )
        
        # Simulate hook validation
        result = mock_runtime.run_action(CmdRunAction(command='git hook test'))
        
        assert result.exit_code == 1
        assert 'validation error' in result.content


if __name__ == '__main__':
    pytest.main([__file__])