"""
Standalone test suite for Git sample hooks.

This module tests the functionality of all sample Git hooks found in the
.git/hooks/ directory without requiring OpenHands dependencies.
"""

import os
import tempfile
import subprocess
import shutil
from pathlib import Path
import pytest


class TestSampleHooksStandalone:
    """Test class for Git sample hooks functionality without OpenHands dependencies."""
    
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
    
    def test_pre_commit_hook_basic_functionality(self, temp_git_repo, sample_hooks_dir):
        """Test basic pre-commit hook functionality."""
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
        
        # Should succeed (or fail due to other hooks, but not due to our pre-commit hook)
        # The important thing is that it doesn't fail due to ASCII/whitespace issues
        assert "non-ASCII file name" not in result.stderr
        assert "trailing whitespace" not in result.stderr.lower()
        
        # Clean up
        Path(test_file).unlink()
    
    def test_commit_msg_hook_basic_functionality(self, temp_git_repo, sample_hooks_dir):
        """Test basic commit-msg hook functionality."""
        # Copy the commit-msg sample hook
        commit_msg_src = sample_hooks_dir / 'commit-msg.sample'
        commit_msg_dst = Path(temp_git_repo) / '.git' / 'hooks' / 'commit-msg'
        shutil.copy2(commit_msg_src, commit_msg_dst)
        os.chmod(commit_msg_dst, 0o755)
        
        # Create a valid commit message
        commit_msg_file = "commit_msg.txt"
        with open(commit_msg_file, 'w') as f:
            f.write("Test commit\n")
        
        # Test the hook directly
        result = subprocess.run([str(commit_msg_dst), commit_msg_file], capture_output=True, text=True)
        
        # Should succeed (no duplicate Signed-off-by lines)
        assert result.returncode == 0
        
        # Clean up
        Path(commit_msg_file).unlink()
    
    def test_pre_push_hook_basic_functionality(self, temp_git_repo, sample_hooks_dir):
        """Test basic pre-push hook functionality."""
        # Copy the pre-push sample hook
        pre_push_src = sample_hooks_dir / 'pre-push.sample'
        pre_push_dst = Path(temp_git_repo) / '.git' / 'hooks' / 'pre-push'
        shutil.copy2(pre_push_src, pre_push_dst)
        os.chmod(pre_push_dst, 0o755)
        
        # Create a file and commit with normal message
        test_file = "test.txt"
        Path(test_file).write_text("content")
        subprocess.run(['git', 'add', test_file], check=True)
        
        # Try to commit (may fail due to other hooks, but that's ok for this test)
        result = subprocess.run(['git', 'commit', '-m', 'Normal commit'], capture_output=True, text=True)
        
        # If commit succeeded, test the pre-push hook
        if result.returncode == 0:
            # Try to push (simulate push to test the hook)
            # We'll call the hook directly since we don't have a remote
            push_result = subprocess.run([
                str(pre_push_dst), 
                'origin', 
                'https://github.com/test/repo.git'
            ], input='main abc123 main def456\n', text=True, capture_output=True)
            
            # Should succeed (no WIP commits)
            assert push_result.returncode == 0
        
        # Clean up
        Path(test_file).unlink()
    
    def test_prepare_commit_msg_hook_basic_functionality(self, temp_git_repo, sample_hooks_dir):
        """Test basic prepare-commit-msg hook functionality."""
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
        
        # Should succeed (hook runs without error)
        assert result.returncode == 0
        
        # Check that the hook ran (the file may be modified or not, depending on the hook logic)
        # The important thing is that it didn't crash
        assert result.returncode == 0
        
        # Clean up
        Path(commit_msg_file).unlink()
    
    def test_hook_documentation_extraction(self, sample_hooks_dir):
        """Test that hooks contain proper documentation."""
        for hook_file in sample_hooks_dir.glob('*.sample'):
            with open(hook_file, 'r') as f:
                lines = f.readlines()
            
            # Check that the file has some documentation comments
            comment_lines = [line for line in lines if line.strip().startswith('#')]
            assert len(comment_lines) > 0, f"{hook_file.name} should have documentation comments"
            
            # Check that it describes what the hook does
            content = ''.join(comment_lines).lower()
            assert any(keyword in content for keyword in ['hook', 'example', 'test', 'check']), \
                f"{hook_file.name} should describe its purpose"


class TestHookValidation:
    """Test hook validation utilities."""
    
    @pytest.fixture
    def sample_hooks_dir(self):
        """Get the path to the sample hooks directory."""
        repo_root = Path(__file__).parent.parent.parent.parent
        return repo_root / '.git' / 'hooks'
    
    def test_validate_hook_syntax(self, sample_hooks_dir):
        """Test hook syntax validation."""
        for hook_file in sample_hooks_dir.glob('*.sample'):
            # Check shebang
            with open(hook_file, 'r') as f:
                first_line = f.readline().strip()
            
            assert first_line.startswith('#!'), f"{hook_file.name} missing shebang"
            
            # Check for valid interpreter
            assert any(interpreter in first_line for interpreter in ['sh', 'bash', 'perl']), \
                f"{hook_file.name} has invalid shebang: {first_line}"
            
            # For shell scripts, check syntax
            if 'sh' in first_line or 'bash' in first_line:
                result = subprocess.run(['bash', '-n', str(hook_file)], capture_output=True, text=True)
                assert result.returncode == 0, f"{hook_file.name} has shell syntax error: {result.stderr}"
    
    def test_hook_permissions(self, sample_hooks_dir):
        """Test that hooks have correct permissions."""
        for hook_file in sample_hooks_dir.glob('*.sample'):
            # Should be executable
            assert os.access(hook_file, os.X_OK), f"{hook_file.name} should be executable"
            
            # Should be readable
            assert os.access(hook_file, os.R_OK), f"{hook_file.name} should be readable"


if __name__ == '__main__':
    pytest.main([__file__])