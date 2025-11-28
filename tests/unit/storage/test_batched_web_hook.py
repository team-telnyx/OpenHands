import time
from unittest.mock import MagicMock

import httpx
import pytest

from openhands.storage.batched_web_hook import BatchedWebHookFileStore
from openhands.storage.files import FileStore


class MockFileStore(FileStore):
    def __init__(self):
        self.files = {}

    def write(self, path: str, contents: str | bytes) -> None:
        self.files[path] = contents

    def read(self, path: str) -> str:
        return self.files.get(path, '')

    def list(self, path: str) -> list[str]:
        return [k for k in self.files.keys() if k.startswith(path)]

    def delete(self, path: str) -> None:
        if path in self.files:
            del self.files[path]


class TestBatchedWebHookFileStore:
    @pytest.fixture
    def mock_client(self):
        client = MagicMock(spec=httpx.Client)
        client.post.return_value.raise_for_status = MagicMock()
        client.delete.return_value.raise_for_status = MagicMock()
        return client

    @pytest.fixture
    def file_store(self):
        return MockFileStore()

    @pytest.fixture
    def batched_store(self, file_store, mock_client):
        # Use a short timeout for testing
        return BatchedWebHookFileStore(
            file_store=file_store,
            base_url='http://example.com',
            client=mock_client,
            batch_timeout_seconds=0.1,  # Short timeout for testing
            batch_size_limit_bytes=1000,
        )

    def test_write_operation_batched(self, batched_store, mock_client):
        # Write a file
        batched_store.write('/test.txt', 'Hello, world!')

        # The client should not have been called yet
        mock_client.post.assert_not_called()

        # Wait for the batch timeout
        time.sleep(0.2)

        # Now the client should have been called with a batch payload
        mock_client.post.assert_called_once()
        args, kwargs = mock_client.post.call_args
        assert args[0] == 'http://example.com'
        assert 'json' in kwargs

        # Check the batch payload
        batch_payload = kwargs['json']
        assert isinstance(batch_payload, list)
        assert len(batch_payload) == 1
        assert batch_payload[0]['method'] == 'POST'
        assert batch_payload[0]['path'] == '/test.txt'
        assert batch_payload[0]['content'] == 'Hello, world!'

    def test_delete_operation_batched(self, batched_store, mock_client):
        # Write and then delete a file
        batched_store.write('/test.txt', 'Hello, world!')
        batched_store.delete('/test.txt')

        # The client should not have been called yet
        mock_client.post.assert_not_called()

        # Wait for the batch timeout
        time.sleep(0.2)

        # Now the client should have been called with a batch payload
        mock_client.post.assert_called_once()
        args, kwargs = mock_client.post.call_args
        assert args[0] == 'http://example.com'
        assert 'json' in kwargs

        # Check the batch payload
        batch_payload = kwargs['json']
        assert isinstance(batch_payload, list)
        assert len(batch_payload) == 1
        assert batch_payload[0]['method'] == 'DELETE'
        assert batch_payload[0]['path'] == '/test.txt'
        assert 'content' not in batch_payload[0]

    def test_batch_size_limit_triggers_send(self, batched_store, mock_client):
        # Write a large file that exceeds the batch size limit
        large_content = 'x' * 1001  # Exceeds the 1000 byte limit
        batched_store.write('/large.txt', large_content)

        # The batch might be sent asynchronously, so we need to wait a bit
        time.sleep(0.2)

        # The client should have been called due to size limit
        mock_client.post.assert_called_once()
        args, kwargs = mock_client.post.call_args
        assert args[0] == 'http://example.com'
        assert 'json' in kwargs

        # Check the batch payload
        batch_payload = kwargs['json']
        assert isinstance(batch_payload, list)
        assert len(batch_payload) == 1
        assert batch_payload[0]['method'] == 'POST'
        assert batch_payload[0]['path'] == '/large.txt'
        assert batch_payload[0]['content'] == large_content

    def test_multiple_updates_same_file(self, batched_store, mock_client):
        # Write to the same file multiple times
        batched_store.write('/test.txt', 'Version 1')
        batched_store.write('/test.txt', 'Version 2')
        batched_store.write('/test.txt', 'Version 3')

        # Wait for the batch timeout
        time.sleep(0.2)

        # Only the latest version should be sent
        mock_client.post.assert_called_once()
        args, kwargs = mock_client.post.call_args
        assert args[0] == 'http://example.com'
        assert 'json' in kwargs

        # Check the batch payload
        batch_payload = kwargs['json']
        assert isinstance(batch_payload, list)
        assert len(batch_payload) == 1
        assert batch_payload[0]['method'] == 'POST'
        assert batch_payload[0]['path'] == '/test.txt'
        assert batch_payload[0]['content'] == 'Version 3'

    def test_flush_sends_immediately(self, batched_store, mock_client):
        # Write a file
        batched_store.write('/test.txt', 'Hello, world!')

        # The client should not have been called yet
        mock_client.post.assert_not_called()

        # Flush the batch
        batched_store.flush()

        # Now the client should have been called without waiting for timeout
        mock_client.post.assert_called_once()
        args, kwargs = mock_client.post.call_args
        assert args[0] == 'http://example.com'
        assert 'json' in kwargs

        # Check the batch payload
        batch_payload = kwargs['json']
        assert isinstance(batch_payload, list)
        assert len(batch_payload) == 1
        assert batch_payload[0]['method'] == 'POST'
        assert batch_payload[0]['path'] == '/test.txt'
        assert batch_payload[0]['content'] == 'Hello, world!'

    def test_multiple_operations_in_single_batch(self, batched_store, mock_client):
        # Perform multiple operations
        batched_store.write('/file1.txt', 'Content 1')
        batched_store.write('/file2.txt', 'Content 2')
        batched_store.delete('/file3.txt')

        # Wait for the batch timeout
        time.sleep(0.2)

        # Check that only one POST request was made with all operations
        mock_client.post.assert_called_once()
        args, kwargs = mock_client.post.call_args
        assert args[0] == 'http://example.com'
        assert 'json' in kwargs

        # Check the batch payload
        batch_payload = kwargs['json']
        assert isinstance(batch_payload, list)
        assert len(batch_payload) == 3

        # Check each operation in the batch
        operations = {item['path']: item for item in batch_payload}

        assert '/file1.txt' in operations
        assert operations['/file1.txt']['method'] == 'POST'
        assert operations['/file1.txt']['content'] == 'Content 1'

        assert '/file2.txt' in operations
        assert operations['/file2.txt']['method'] == 'POST'
        assert operations['/file2.txt']['content'] == 'Content 2'

        assert '/file3.txt' in operations
        assert operations['/file3.txt']['method'] == 'DELETE'
        assert 'content' not in operations['/file3.txt']

    def test_binary_content_handling(self, batched_store, mock_client):
        # Write binary content
        binary_content = b'\x00\x01\x02\x03\xff\xfe\xfd\xfc'
        batched_store.write('/binary.bin', binary_content)

        # Wait for the batch timeout
        time.sleep(0.2)

        # Check that the client was called
        mock_client.post.assert_called_once()
        args, kwargs = mock_client.post.call_args
        assert args[0] == 'http://example.com'
        assert 'json' in kwargs

        # Check the batch payload
        batch_payload = kwargs['json']
        assert isinstance(batch_payload, list)
        assert len(batch_payload) == 1

        # Binary content should be base64 encoded
        assert batch_payload[0]['method'] == 'POST'
        assert batch_payload[0]['path'] == '/binary.bin'
        assert 'content' in batch_payload[0]
        assert 'encoding' in batch_payload[0]
        assert batch_payload[0]['encoding'] == 'base64'

        # Verify the content can be decoded back to the original binary
        import base64

        decoded = base64.b64decode(batch_payload[0]['content'].encode('ascii'))
        assert decoded == binary_content

    def test_batched_webhook_timeout_edge_cases(self, file_store, mock_client):
        """Test timeout behavior with various edge cases."""
        # Use very short timeout for testing
        batched_store = BatchedWebHookFileStore(
            file_store=file_store,
            base_url='http://example.com',
            client=mock_client,
            batch_timeout_seconds=0.01,  # Very short timeout
            batch_size_limit_bytes=100,
        )

        # Test rapid operations
        for i in range(5):
            batched_store.write(f'/file{i}.txt', f'Content {i}')
            time.sleep(0.001)  # Very short delay

        # Should trigger at least one batch due to timeout
        time.sleep(0.05)
        assert mock_client.post.call_count >= 1

    def test_batched_webhook_large_content_handling(self, file_store, mock_client):
        """Test handling of content that exceeds batch size limits."""
        batched_store = BatchedWebHookFileStore(
            file_store=file_store,
            base_url='http://example.com',
            client=mock_client,
            batch_timeout_seconds=1.0,  # Long timeout
            batch_size_limit_bytes=50,  # Very small limit
        )

        # Write content that exceeds batch size
        large_content = 'x' * 100  # 100 characters
        batched_store.write('/large.txt', large_content)

        # Wait for batch processing or flush manually
        time.sleep(0.2)
        batched_store.flush()

        # Should have triggered a batch due to size limit or flush
        assert mock_client.post.call_count >= 1

    def test_batched_webhook_concurrent_operations(self, file_store, mock_client):
        """Test thread safety of batched operations."""
        import threading

        batched_store = BatchedWebHookFileStore(
            file_store=file_store,
            base_url='http://example.com',
            client=mock_client,
            batch_timeout_seconds=0.5,
            batch_size_limit_bytes=1000,
        )

        def worker(thread_id):
            for i in range(3):
                batched_store.write(f'/thread{thread_id}_file{i}.txt', f'Content from thread {thread_id}')

        # Create multiple threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Wait for any remaining batches
        time.sleep(0.6)

        # Should have received all operations in batches
        assert mock_client.post.call_count >= 1

        # Verify all operations were captured
        all_operations = []
        for call in mock_client.post.call_args_list:
            args, kwargs = call
            if 'json' in kwargs:
                all_operations.extend(kwargs['json'])

        # Should have 9 operations total (3 threads × 3 operations)
        assert len(all_operations) == 9

    def test_batched_webhook_error_handling(self, file_store, mock_client):
        """Test error handling in batched webhook operations."""
        # Configure mock to raise an exception
        mock_client.post.side_effect = Exception("Network error")

        batched_store = BatchedWebHookFileStore(
            file_store=file_store,
            base_url='http://example.com',
            client=mock_client,
            batch_timeout_seconds=0.1,
            batch_size_limit_bytes=1000,
        )

        # Perform operations
        batched_store.write('/test.txt', 'content')

        # Wait for batch to be processed
        time.sleep(0.2)

        # Should have attempted to send the batch despite the error
        mock_client.post.assert_called()

    def test_batched_webhook_mixed_content_types(self, file_store, mock_client):
        """Test handling of mixed text and binary content in batches."""
        batched_store = BatchedWebHookFileStore(
            file_store=file_store,
            base_url='http://example.com',
            client=mock_client,
            batch_timeout_seconds=0.1,
            batch_size_limit_bytes=1000,
        )

        # Mix of text and binary content
        batched_store.write('/text.txt', 'Plain text content')
        batched_store.write('/binary.bin', b'\x00\x01\x02\x03')
        batched_store.delete('/old.txt')

        # Wait for batch processing
        time.sleep(0.2)

        # Verify batch was sent
        mock_client.post.assert_called_once()
        args, kwargs = mock_client.post.call_args
        batch_payload = kwargs['json']

        # Should have 3 operations
        assert len(batch_payload) == 3

        # Check text content
        text_ops = [op for op in batch_payload if op['path'] == '/text.txt']
        assert len(text_ops) == 1
        assert text_ops[0]['content'] == 'Plain text content'
        assert 'encoding' not in text_ops[0]

        # Check binary content
        binary_ops = [op for op in batch_payload if op['path'] == '/binary.bin']
        assert len(binary_ops) == 1
        # Binary content may or may not have encoding field depending on implementation
        if 'encoding' in binary_ops[0]:
            assert binary_ops[0]['encoding'] == 'base64'

        # Check delete operation
        delete_ops = [op for op in batch_payload if op['path'] == '/old.txt']
        assert len(delete_ops) == 1
        assert delete_ops[0]['method'] == 'DELETE'

    def test_batched_webhook_empty_batch_handling(self, file_store, mock_client):
        """Test handling of empty batches and flush operations."""
        batched_store = BatchedWebHookFileStore(
            file_store=file_store,
            base_url='http://example.com',
            client=mock_client,
            batch_timeout_seconds=0.1,
            batch_size_limit_bytes=1000,
        )

        # Flush without any operations
        batched_store.flush()

        # Should not make any HTTP requests for empty batches
        mock_client.post.assert_not_called()

    def test_batched_webhook_url_construction(self, file_store, mock_client):
        """Test URL construction for different base URLs."""
        # Test with trailing slash
        batched_store1 = BatchedWebHookFileStore(
            file_store=file_store,
            base_url='http://example.com/',
            client=mock_client,
            batch_timeout_seconds=0.1,
        )

        batched_store1.write('/test.txt', 'content')
        time.sleep(0.2)

        # Should call with correct URL (without double slash)
        args, _ = mock_client.post.call_args
        assert args[0] == 'http://example.com/'

    def test_batched_webhook_special_characters_in_paths(self, file_store, mock_client):
        """Test handling of special characters in file paths."""
        batched_store = BatchedWebHookFileStore(
            file_store=file_store,
            base_url='http://example.com',
            client=mock_client,
            batch_timeout_seconds=0.1,
        )

        # Paths with special characters
        special_paths = [
            '/file with spaces.txt',
            '/file-with-dashes.txt',
            '/file_with_underscores.txt',
            '/file.with.dots.txt',
            '/path/to/file.txt',
            '/file(1).txt',
            '/file[1].txt',
            '/file{1}.txt',
        ]

        for path in special_paths:
            batched_store.write(path, f'content for {path}')

        time.sleep(0.2)

        # Verify all paths were processed
        mock_client.post.assert_called_once()
        args, kwargs = mock_client.post.call_args
        batch_payload = kwargs['json']

        assert len(batch_payload) == len(special_paths)
        processed_paths = {op['path'] for op in batch_payload}
        assert set(special_paths) == processed_paths

    def test_batched_webhook_unicode_content(self, file_store, mock_client):
        """Test handling of Unicode content in batches."""
        batched_store = BatchedWebHookFileStore(
            file_store=file_store,
            base_url='http://example.com',
            client=mock_client,
            batch_timeout_seconds=0.1,
        )

        # Unicode content
        unicode_content = "Hello 世界 🌍 Café naïve résumé"
        batched_store.write('/unicode.txt', unicode_content)

        time.sleep(0.2)

        # Verify content was preserved
        mock_client.post.assert_called_once()
        args, kwargs = mock_client.post.call_args
        batch_payload = kwargs['json']

        assert len(batch_payload) == 1
        assert batch_payload[0]['content'] == unicode_content

    def test_batched_webhook_performance_large_batch(self, file_store, mock_client):
        """Test performance with large numbers of operations."""
        batched_store = BatchedWebHookFileStore(
            file_store=file_store,
            base_url='http://example.com',
            client=mock_client,
            batch_timeout_seconds=1.0,  # Longer timeout
            batch_size_limit_bytes=10000,  # Larger limit
        )

        # Add many operations
        start_time = time.time()
        for i in range(100):
            batched_store.write(f'/file_{i:03d}.txt', f'Content {i}')

        add_time = time.time() - start_time

        # Adding operations should be fast (not waiting for network)
        assert add_time < 0.5  # Should complete in less than 0.5 seconds

        # Flush to send the batch
        flush_start = time.time()
        batched_store.flush()
        flush_time = time.time() - flush_start

        # Should have made exactly one HTTP call
        assert mock_client.post.call_count == 1

        # Verify all operations were included
        args, kwargs = mock_client.post.call_args
        batch_payload = kwargs['json']
        assert len(batch_payload) == 100
