# Hook Testing Guide

This guide provides comprehensive information about testing hooks in the OpenHands repository.

## Overview

The OpenHands repository includes several types of hooks that need automated testing:

1. **Web Hooks** (`openhands/storage/`)
   - `web_hook.py` - Basic webhook file store
   - `batched_web_hook.py` - Batched webhook file store

2. **Git Hooks** (`openhands/runtime/`)
   - Git hook setup and management functionality

## Automated Testing Infrastructure

### Test Script

The main testing automation is handled by `scripts/test_hooks.py`. This script provides:

- Comprehensive testing of all hook implementations
- CI/CD integration support
- Coverage reporting
- Verbose output options
- Selective testing by hook type

#### Usage

```bash
# Test all hooks
python scripts/test_hooks.py

# Test only web hooks
python scripts/test_hooks.py --webhook

# Test only git hooks
python scripts/test_hooks.py --git-hook

# Enable verbose output
python scripts/test_hooks.py --verbose

# Generate coverage report
python scripts/test_hooks.py --coverage

# Combine options
python scripts/test_hooks.py --webhook --verbose --coverage
```

### CI/CD Integration

The GitHub Actions workflow (`.github/workflows/test-hooks.yml`) automatically runs tests when:

- Code is pushed to `main` or `develop` branches
- Pull requests are created/updated
- Manually triggered via workflow dispatch

The workflow:
- Tests on multiple Python versions (3.12, 3.13)
- Generates coverage reports
- Comments on PRs with test results
- Uploads coverage artifacts

## Test Structure

### Web Hook Tests

#### Basic Web Hook (`tests/unit/storage/test_web_hook.py`)

Tests for `WebHookFileStore` include:

- **Initialization Tests**
  - Default client creation
  - Custom client injection
  - Configuration validation

- **Operation Tests**
  - File write operations and webhook triggering
  - File delete operations and webhook triggering
  - Binary content handling
  - URL construction and path handling

- **Reliability Tests**
  - Retry mechanism on failures
  - Failure handling after max retries
  - Multiple operations handling

- **Edge Case Tests**
  - Empty path handling
  - Special characters in paths
  - Concurrent operations

#### Batched Web Hook (`tests/unit/storage/test_batched_web_hook.py`)

Tests for `BatchedWebHookFileStore` include:

- **Batching Behavior**
  - Timeout-based batch sending
  - Size limit-based batch sending
  - Multiple operations in single batch

- **Content Handling**
  - Binary content with base64 encoding
  - UTF-8 text content
  - Mixed content types

- **Batch Management**
  - Flush functionality
  - Timer management
  - Thread safety

### Git Hook Tests (`tests/unit/runtime/test_git_hooks.py`)

Tests for git hook functionality include:

- **Setup Tests**
  - Successful hook installation
  - Directory creation
  - Permission handling

- **Edge Cases**
  - Missing script files
  - Existing hook preservation
  - Failure scenarios

## Running Tests Locally

### Prerequisites

1. Install dependencies:
```bash
poetry install --with test
```

2. Activate the virtual environment:
```bash
source $(poetry env info --path)/bin/activate
```

### Running Tests

#### Quick Test
```bash
python scripts/test_hooks.py
```

#### Detailed Test with Coverage
```bash
python scripts/test_hooks.py --verbose --coverage
```

#### Individual Test Files
```bash
# Test web hooks only
pytest tests/unit/storage/test_web_hook.py -v

# Test batched web hooks only
pytest tests/unit/storage/test_batched_web_hook.py -v

# Test git hooks only
pytest tests/unit/runtime/test_git_hooks.py -v
```

## Coverage Requirements

The test suite aims for:

- **Line Coverage**: > 90%
- **Branch Coverage**: > 85%
- **Function Coverage**: 100%

Coverage reports are generated in:
- Terminal output (summary)
- HTML report (`htmlcov/index.html`)
- CI/CD artifacts

## Adding New Hook Tests

When adding new hook implementations:

1. **Create Test File**
   - Follow naming convention: `test_<hook_name>.py`
   - Place in appropriate directory under `tests/unit/`

2. **Test Structure**
   ```python
   class TestNewHook:
       @pytest.fixture
       def setup_hook(self):
           # Setup test fixture
           pass
       
       def test_basic_functionality(self, setup_hook):
           # Test basic functionality
           pass
       
       def test_edge_cases(self, setup_hook):
           # Test edge cases
           pass
       
       def test_error_handling(self, setup_hook):
           # Test error scenarios
           pass
   ```

3. **Update Test Script**
   - Add new hook type to `scripts/test_hooks.py`
   - Update CI/CD workflow if needed

4. **Documentation**
   - Update this documentation file
   - Add examples and usage instructions

## Best Practices

### Test Design

1. **Isolation**: Each test should be independent
2. **Mocking**: Use mocks for external dependencies (HTTP clients, file system)
3. **Assertions**: Be specific with assertions
4. **Edge Cases**: Test both happy path and error scenarios

### Async Testing

For webhook tests that involve async operations:

1. **Timing**: Use `time.sleep()` to allow async operations to complete
2. **Mocking**: Mock async components properly
3. **Cleanup**: Ensure proper cleanup after tests

### Coverage

1. **Branch Coverage**: Test all conditional branches
2. **Exception Handling**: Test all exception paths
3. **Integration**: Test component interactions

## Troubleshooting

### Common Issues

1. **Async Test Failures**
   - Increase sleep time for async operations
   - Check mock configurations

2. **Import Errors**
   - Ensure proper Python path setup
   - Install all dependencies

3. **Permission Issues**
   - Check file permissions for test files
   - Ensure proper directory structure

### Debug Mode

Run tests with extra debugging:
```bash
python scripts/test_hooks.py --verbose
```

Or use pytest directly:
```bash
pytest tests/unit/storage/test_web_hook.py -vv -s
```

## Continuous Integration

The automated testing ensures:

1. **Quality**: All hooks are thoroughly tested
2. **Consistency**: Tests run the same way locally and in CI
3. **Coverage**: High test coverage is maintained
4. **Regression**: New changes don't break existing functionality

### CI/CD Pipeline

1. **Trigger**: Automatic on relevant file changes
2. **Matrix Testing**: Multiple Python versions
3. **Coverage**: Automatic coverage reporting
4. **Notifications**: PR comments with results
5. **Artifacts**: Coverage reports stored as artifacts

## Future Enhancements

Planned improvements to the testing infrastructure:

1. **Performance Testing**: Load testing for webhooks
2. **Integration Testing**: End-to-end hook testing
3. **Security Testing**: Hook security validation
4. **Monitoring**: Test execution monitoring and alerting