# Git Hooks Testing Framework

This document describes the automated testing framework for Git sample hooks in the OpenHands repository.

## Overview

The Git hooks testing framework ensures that all sample Git hooks in `.git/hooks/` are properly tested and validated. This provides confidence that the hooks work as expected and can be used as reference implementations.

## Test Structure

### Test Files

- `tests/unit/git_hooks/test_sample_hooks_standalone.py` - Standalone tests that don't require OpenHands dependencies
- `tests/unit/git_hooks/test_sample_hooks.py` - Full integration tests with OpenHands runtime (requires full dependencies)
- `tests/unit/git_hooks/hook_test_utils.py` - Utility functions and classes for hook testing
- `tests/unit/git_hooks/__init__.py` - Package initialization

### Test Coverage

The framework tests the following aspects of Git sample hooks:

#### 1. Hook Existence and Permissions
- Verifies all expected sample hooks exist
- Ensures hooks are executable
- Checks proper file permissions

#### 2. Hook Syntax Validation
- Validates shebang lines
- Checks shell script syntax
- Ensures proper interpreter specification

#### 3. Functional Testing
- **pre-commit hook**: Tests ASCII filename validation and whitespace checks
- **pre-push hook**: Tests WIP (Work In Progress) commit detection
- **commit-msg hook**: Tests duplicate Signed-off-by line detection
- **prepare-commit-msg hook**: Tests help text removal functionality
- **Other hooks**: Basic functionality validation

#### 4. Documentation Validation
- Ensures hooks contain proper documentation comments
- Validates that hooks describe their purpose

## Running Tests

### Quick Start

```bash
# Run all Git hooks tests
make test-git-hooks

# Or run the test script directly
./scripts/test_git_hooks.sh
```

### Individual Test Suites

```bash
# Run standalone tests (no dependencies required)
python -m pytest tests/unit/git_hooks/test_sample_hooks_standalone.py -v

# Run full integration tests (requires OpenHands dependencies)
python -m pytest tests/unit/git_hooks/test_sample_hooks.py -v

# Run specific test
python -m pytest tests/unit/git_hooks/test_sample_hooks_standalone.py::TestSampleHooksStandalone::test_all_sample_hooks_exist_and_executable -v
```

### With Coverage

```bash
# Install coverage tool
pip install coverage

# Run tests with coverage
coverage run -m pytest tests/unit/git_hooks/test_sample_hooks_standalone.py
coverage report -m
coverage html  # Generate HTML report
```

## Test Framework Components

### HookTestEnvironment

A context manager that creates a temporary Git repository for testing hooks:

```python
with HookTestEnvironment() as env:
    # Create files, install hooks, run tests
    env.create_file("test.txt", "content")
    env.install_hook("pre-commit", hook_source_path)
    result = env.add_and_commit("test.txt", "test commit")
```

### HookTestCase

A class for defining structured test cases:

```python
case = HookTestCase("test_name", "Test description")
case.add_setup_action({'type': 'create_file', 'filename': 'test.txt', 'content': 'content'})
case.add_test_action({'type': 'commit', 'message': 'test commit'})
case.set_expected_result(0)
```

### Utility Functions

- `validate_hook_syntax()` - Validates hook script syntax
- `get_hook_documentation()` - Extracts documentation from hooks
- `execute_test_case()` - Executes structured test cases

## CI/CD Integration

The Git hooks tests are integrated into the development workflow:

### Makefile Targets

- `make test-git-hooks` - Run all Git hooks tests
- `make test` - Run all tests (includes frontend tests)

### Test Script

The `scripts/test_git_hooks.sh` script provides:
- Automated test execution
- Dependency checking
- Hook validation
- Coverage reporting
- Colored output and status reporting

### GitHub Actions

The tests can be integrated into CI/CD pipelines by adding:

```yaml
- name: Test Git Hooks
  run: make test-git-hooks
```

## Sample Hooks Tested

The framework tests the following sample hooks:

| Hook | Purpose | Test Coverage |
|------|---------|---------------|
| `applypatch-msg.sample` | Validate patch commit messages | ✅ Syntax & permissions |
| `commit-msg.sample` | Validate commit messages | ✅ Full functionality |
| `fsmonitor-watchman.sample` | File system monitoring | ✅ Syntax & permissions |
| `post-update.sample` | Post-update notifications | ✅ Syntax & permissions |
| `pre-applypatch.sample` | Pre-patch validation | ✅ Syntax & permissions |
| `pre-commit.sample` | Pre-commit validation | ✅ Full functionality |
| `pre-merge-commit.sample` | Pre-merge validation | ✅ Syntax & permissions |
| `pre-push.sample` | Pre-push validation | ✅ Full functionality |
| `pre-rebase.sample` | Pre-rebase validation | ✅ Syntax & permissions |
| `pre-receive.sample` | Pre-receive validation | ✅ Syntax & permissions |
| `prepare-commit-msg.sample` | Commit message preparation | ✅ Full functionality |
| `push-to-checkout.sample` | Push to checkout validation | ✅ Syntax & permissions |
| `sendemail-validate.sample` | Email validation | ✅ Syntax & permissions |
| `update.sample` | Update validation | ✅ Syntax & permissions |

## Adding New Tests

### Adding a New Hook Test

1. Create a test method in the appropriate test class
2. Use the `temp_git_repo` fixture for isolated testing
3. Copy the sample hook to the test repository
4. Test the hook's functionality
5. Clean up test artifacts

Example:

```python
def test_new_hook_functionality(self, temp_git_repo, sample_hooks_dir):
    """Test new hook functionality."""
    # Copy the hook
    hook_src = sample_hooks_dir / 'new-hook.sample'
    hook_dst = Path(temp_git_repo) / '.git' / 'hooks' / 'new-hook'
    shutil.copy2(hook_src, hook_dst)
    os.chmod(hook_dst, 0o755)
    
    # Test functionality
    # ... test logic here ...
    
    # Assert results
    assert result.returncode == expected_code
```

### Adding Utility Functions

Add new utility functions to `hook_test_utils.py`:

```python
def new_utility_function(hook_path: Path) -> bool:
    """New utility function description."""
    # Implementation
    return result
```

## Troubleshooting

### Common Issues

1. **Permission Denied**: Ensure hooks are executable (`chmod +x`)
2. **Missing Dependencies**: Install required packages with `pip install pytest`
3. **Git Configuration**: Ensure git user is configured in test environments
4. **Hook Conflicts**: Existing hooks may interfere with test hooks

### Debug Mode

Run tests with verbose output:

```bash
python -m pytest tests/unit/git_hooks/ -v -s
```

### Test Isolation

Tests use temporary directories to ensure isolation. If tests interfere with each other, check that cleanup is properly implemented.

## Best Practices

1. **Isolation**: Each test should be independent and isolated
2. **Cleanup**: Always clean up temporary files and repositories
3. **Assertions**: Use specific assertions to validate expected behavior
4. **Documentation**: Document test purpose and expected behavior
5. **Error Handling**: Handle expected errors gracefully
6. **Coverage**: Aim for comprehensive test coverage of hook functionality

## Contributing

When contributing to the Git hooks testing framework:

1. Add tests for new functionality
2. Update documentation
3. Ensure all tests pass
4. Follow existing code style and patterns
5. Add utility functions for common testing patterns

## Future Enhancements

Potential improvements to the testing framework:

- Performance testing for hooks
- Integration with more CI/CD platforms
- Automated hook generation from templates
- Hook performance benchmarking
- Cross-platform compatibility testing