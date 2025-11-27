"""
Utility functions for testing Git hooks.

This module provides helper functions and classes to facilitate
testing of Git sample hooks in various scenarios.
"""

import os
import tempfile
import subprocess
import shutil
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import pytest


class HookTestEnvironment:
    """A test environment for Git hooks testing."""
    
    def __init__(self):
        self.temp_dir = None
        self.original_dir = os.getcwd()
        self.hooks_dir = None
        
    def __enter__(self):
        """Set up the test environment."""
        self.temp_dir = tempfile.mkdtemp()
        os.chdir(self.temp_dir)
        
        # Initialize git repo
        subprocess.run(['git', 'init'], check=True, capture_output=True)
        subprocess.run(['git', 'config', 'user.name', 'Test User'], check=True)
        subprocess.run(['git', 'config', 'user.email', 'test@example.com'], check=True)
        
        self.hooks_dir = Path(self.temp_dir) / '.git' / 'hooks'
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up the test environment."""
        os.chdir(self.original_dir)
        if self.temp_dir:
            shutil.rmtree(self.temp_dir)
    
    def install_hook(self, hook_name: str, source_path: Path) -> Path:
        """Install a hook from source to the test environment."""
        hook_path = self.hooks_dir / hook_name
        shutil.copy2(source_path, hook_path)
        os.chmod(hook_path, 0o755)
        return hook_path
    
    def create_file(self, filename: str, content: str) -> Path:
        """Create a file in the test repository."""
        file_path = Path(filename)
        file_path.write_text(content)
        return file_path
    
    def add_and_commit(self, filename: str, message: str) -> subprocess.CompletedProcess:
        """Add and commit a file."""
        subprocess.run(['git', 'add', filename], check=True)
        return subprocess.run(['git', 'commit', '-m', message], capture_output=True, text=True)
    
    def run_hook(self, hook_path: Path, args: List[str], input_text: Optional[str] = None) -> subprocess.CompletedProcess:
        """Run a hook with given arguments."""
        cmd = [str(hook_path)] + args
        if input_text:
            return subprocess.run(cmd, input=input_text, text=True, capture_output=True)
        else:
            return subprocess.run(cmd, capture_output=True, text=True)


class HookTestCase:
    """Base class for hook test cases."""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.setup_actions = []
        self.test_actions = []
        self.expected_result = None
    
    def add_setup_action(self, action: Dict):
        """Add a setup action for the test case."""
        self.setup_actions.append(action)
    
    def add_test_action(self, action: Dict):
        """Add a test action for the test case."""
        self.test_actions.append(action)
    
    def set_expected_result(self, exit_code: int, output_contains: Optional[str] = None):
        """Set the expected result for the test case."""
        self.expected_result = {
            'exit_code': exit_code,
            'output_contains': output_contains
        }


def create_test_cases_for_pre_commit_hook() -> List[HookTestCase]:
    """Create test cases for the pre-commit hook."""
    test_cases = []
    
    # Test case 1: Non-ASCII filename should fail
    case1 = HookTestCase(
        "non_ascii_filename",
        "Test that pre-commit hook rejects non-ASCII filenames"
    )
    case1.add_setup_action({
        'type': 'create_file',
        'filename': 'tést.txt',
        'content': 'test content'
    })
    case1.add_test_action({
        'type': 'commit',
        'message': 'test commit'
    })
    case1.set_expected_result(1, "non-ASCII file name")
    test_cases.append(case1)
    
    # Test case 2: Trailing whitespace should fail
    case2 = HookTestCase(
        "trailing_whitespace",
        "Test that pre-commit hook rejects trailing whitespace"
    )
    case2.add_setup_action({
        'type': 'create_file',
        'filename': 'test.txt',
        'content': 'content with trailing space   \n'
    })
    case2.add_test_action({
        'type': 'commit',
        'message': 'test commit'
    })
    case2.set_expected_result(1, "trailing whitespace")
    test_cases.append(case2)
    
    # Test case 3: Valid file should succeed
    case3 = HookTestCase(
        "valid_file",
        "Test that pre-commit hook accepts valid files"
    )
    case3.add_setup_action({
        'type': 'create_file',
        'filename': 'test.txt',
        'content': 'valid content\n'
    })
    case3.add_test_action({
        'type': 'commit',
        'message': 'test commit'
    })
    case3.set_expected_result(0)
    test_cases.append(case3)
    
    return test_cases


def create_test_cases_for_pre_push_hook() -> List[HookTestCase]:
    """Create test cases for the pre-push hook."""
    test_cases = []
    
    # Test case 1: WIP commit should fail
    case1 = HookTestCase(
        "wip_commit_detection",
        "Test that pre-push hook rejects WIP commits"
    )
    case1.add_setup_action({
        'type': 'create_file',
        'filename': 'test.txt',
        'content': 'content'
    })
    case1.add_setup_action({
        'type': 'commit',
        'message': 'WIP: work in progress'
    })
    case1.add_test_action({
        'type': 'run_hook',
        'args': ['origin', 'https://github.com/test/repo.git'],
        'input': 'main abc123 main def456\n'
    })
    case1.set_expected_result(1, "WIP commit")
    test_cases.append(case1)
    
    return test_cases


def create_test_cases_for_commit_msg_hook() -> List[HookTestCase]:
    """Create test cases for the commit-msg hook."""
    test_cases = []
    
    # Test case 1: Duplicate Signed-off-by should fail
    case1 = HookTestCase(
        "duplicate_signed_off_by",
        "Test that commit-msg hook rejects duplicate Signed-off-by lines"
    )
    case1.add_test_action({
        'type': 'run_hook',
        'args': ['commit_msg.txt'],
        'input': None,
        'setup_file': {
            'filename': 'commit_msg.txt',
            'content': 'Test commit\n\nSigned-off-by: Test User <test@example.com>\nSigned-off-by: Test User <test@example.com>\n'
        }
    })
    case1.set_expected_result(1, "Duplicate Signed-off-by")
    test_cases.append(case1)
    
    # Test case 2: Valid commit message should succeed
    case2 = HookTestCase(
        "valid_commit_message",
        "Test that commit-msg hook accepts valid commit messages"
    )
    case2.add_test_action({
        'type': 'run_hook',
        'args': ['commit_msg.txt'],
        'input': None,
        'setup_file': {
            'filename': 'commit_msg.txt',
            'content': 'Test commit\n\nSigned-off-by: Test User <test@example.com>\n'
        }
    })
    case2.set_expected_result(0)
    test_cases.append(case2)
    
    return test_cases


def execute_test_case(test_case: HookTestCase, env: HookTestEnvironment, hook_path: Path) -> bool:
    """Execute a single test case."""
    try:
        # Execute setup actions
        for action in test_case.setup_actions:
            if action['type'] == 'create_file':
                env.create_file(action['filename'], action['content'])
            elif action['type'] == 'commit':
                env.add_and_commit(action['filename'], action['message'])
        
        # Execute test actions
        results = []
        for action in test_case.test_actions:
            if action['type'] == 'commit':
                result = env.add_and_commit(action['filename'], action['message'])
                results.append(result)
            elif action['type'] == 'run_hook':
                if 'setup_file' in action:
                    env.create_file(action['setup_file']['filename'], action['setup_file']['content'])
                result = env.run_hook(hook_path, action['args'], action.get('input'))
                results.append(result)
        
        # Check expected results
        if test_case.expected_result:
            for result in results:
                if result.returncode != test_case.expected_result['exit_code']:
                    return False
                if test_case.expected_result['output_contains']:
                    if test_case.expected_result['output_contains'] not in result.stderr and \
                       test_case.expected_result['output_contains'] not in result.stdout:
                        return False
        
        return True
        
    except Exception as e:
        print(f"Error executing test case {test_case.name}: {e}")
        return False


def validate_hook_syntax(hook_path: Path) -> Tuple[bool, str]:
    """Validate the syntax of a hook script."""
    try:
        with open(hook_path, 'r') as f:
            first_line = f.readline().strip()
        
        if not first_line.startswith('#!'):
            return False, "Missing shebang line"
        
        if 'sh' not in first_line and 'bash' not in first_line and 'perl' not in first_line:
            return False, f"Invalid shebang: {first_line}"
        
        # Try to validate shell syntax
        if 'sh' in first_line or 'bash' in first_line:
            result = subprocess.run(['bash', '-n', str(hook_path)], capture_output=True, text=True)
            if result.returncode != 0:
                return False, f"Shell syntax error: {result.stderr}"
        
        return True, "Syntax is valid"
        
    except Exception as e:
        return False, f"Error validating syntax: {e}"


def get_hook_documentation(hook_path: Path) -> str:
    """Extract documentation from a hook script."""
    try:
        with open(hook_path, 'r') as f:
            lines = f.readlines()
        
        # Extract comment lines at the beginning
        doc_lines = []
        in_doc_block = False
        
        for line in lines:
            line = line.strip()
            if line.startswith('#'):
                doc_lines.append(line[1:].strip())
                in_doc_block = True
            elif in_doc_block and line == '':
                doc_lines.append('')
            elif in_doc_block and not line.startswith('#'):
                break
        
        return '\n'.join(doc_lines).strip()
        
    except Exception as e:
        return f"Error extracting documentation: {e}"