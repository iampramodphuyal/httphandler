"""Tests for the HTTPHandler simple interface."""

import pytest
import warnings
from unittest.mock import Mock, patch, MagicMock

from http_client import HTTPHandler, NoResponseError, Response, Request


class TestHTTPHandlerInit:
    """Tests for HTTPHandler initialization."""

    def test_init_defaults(self):
        """Test default initialization values."""
        handler = HTTPHandler()
        assert handler.persist_session is False
        assert handler._timeout == 30.0
        assert handler._connect_timeout == 10.0
        assert handler._verify_ssl is True
        assert handler._http_version == "auto"
        assert handler._proxy is None
        assert handler._max_retries == 3
        assert handler._default_headers == {}
        handler.close()

    def test_init_with_custom_values(self):
        """Test initialization with custom values."""
        handler = HTTPHandler(
            persist_session=True,
            timeout=60.0,
            connect_timeout=20.0,
            verify_ssl=False,
            http_version="2",
            proxy="socks5://localhost:1080",
            max_retries=5,
            headers={"User-Agent": "Test/1.0"},
        )
        assert handler.persist_session is True
        assert handler._timeout == 60.0
        assert handler._connect_timeout == 20.0
        assert handler._verify_ssl is False
        assert handler._http_version == "2"
        assert handler._proxy == "socks5://localhost:1080"
        assert handler._max_retries == 5
        assert handler._default_headers == {"User-Agent": "Test/1.0"}
        handler.close()

    def test_init_creates_cookie_store_when_persist_session(self):
        """Test that cookie store is created when persist_session=True."""
        handler = HTTPHandler(persist_session=True)
        assert handler._cookie_store is not None
        handler.close()

    def test_init_no_cookie_store_by_default(self):
        """Test that cookie store is None by default."""
        handler = HTTPHandler()
        assert handler._cookie_store is None
        handler.close()


class TestHTTPHandlerResponseHelpers:
    """Tests for response helper methods."""

    def test_get_status_code_no_response(self):
        """Test get_status_code raises when no response."""
        handler = HTTPHandler()
        with pytest.raises(NoResponseError):
            handler.get_status_code()
        handler.close()

    def test_get_cookies_no_response(self):
        """Test get_cookies raises when no response."""
        handler = HTTPHandler()
        with pytest.raises(NoResponseError):
            handler.get_cookies()
        handler.close()

    def test_get_headers_no_response(self):
        """Test get_headers raises when no response."""
        handler = HTTPHandler()
        with pytest.raises(NoResponseError):
            handler.get_headers()
        handler.close()

    def test_get_bandwidth_no_response(self):
        """Test get_bandwidth raises when no response."""
        handler = HTTPHandler()
        with pytest.raises(NoResponseError):
            handler.get_bandwidth()
        handler.close()

    def test_get_elapsed_no_response(self):
        """Test get_elapsed raises when no response."""
        handler = HTTPHandler()
        with pytest.raises(NoResponseError):
            handler.get_elapsed()
        handler.close()

    def test_get_content_length_no_response(self):
        """Test get_content_length raises when no response."""
        handler = HTTPHandler()
        with pytest.raises(NoResponseError):
            handler.get_content_length()
        handler.close()

    def test_get_response_no_response(self):
        """Test get_response raises when no response."""
        handler = HTTPHandler()
        with pytest.raises(NoResponseError):
            handler.get_response()
        handler.close()

    def test_response_helpers_with_mock_response(self):
        """Test response helpers return correct values from response."""
        handler = HTTPHandler()
        # Manually set a mock response
        handler._last_response = Response(
            status_code=200,
            headers={"Content-Type": "application/json"},
            content=b"Hello, World!",
            url="https://example.com",
            cookies={"session": "abc123"},
            elapsed=0.5,
        )

        assert handler.get_status_code() == 200
        assert handler.get_cookies() == {"session": "abc123"}
        assert handler.get_headers() == {"Content-Type": "application/json"}
        assert handler.get_elapsed() == 0.5
        assert handler.get_content_length() == 13

        # Test bandwidth calculation (13 bytes / 0.5 sec = 26 bytes/sec)
        assert handler.get_bandwidth() == 26.0

        handler.close()

    def test_bandwidth_zero_elapsed(self):
        """Test bandwidth returns 0 when elapsed is 0."""
        handler = HTTPHandler()
        handler._last_response = Response(
            status_code=200,
            headers={},
            content=b"test",
            url="https://example.com",
            elapsed=0.0,
        )
        assert handler.get_bandwidth() == 0.0
        handler.close()


class TestHTTPHandlerSessionControl:
    """Tests for session control methods."""

    def test_persist_session_property(self):
        """Test persist_session getter."""
        handler = HTTPHandler(persist_session=False)
        assert handler.persist_session is False
        handler.close()

        handler = HTTPHandler(persist_session=True)
        assert handler.persist_session is True
        handler.close()

    def test_persist_session_setter_enable(self):
        """Test enabling session persistence."""
        handler = HTTPHandler(persist_session=False)
        assert handler._cookie_store is None

        handler.persist_session = True
        assert handler._cookie_store is not None
        assert handler.persist_session is True
        handler.close()

    def test_persist_session_setter_disable(self):
        """Test disabling session persistence."""
        handler = HTTPHandler(persist_session=True)
        assert handler._cookie_store is not None

        handler.persist_session = False
        assert handler._cookie_store is None
        assert handler.persist_session is False
        handler.close()

    def test_reset_session(self):
        """Test reset_session clears cookies and response."""
        handler = HTTPHandler(persist_session=True)
        handler._cookie_store.set("session", "value123", "example.com")
        handler._last_response = Response(
            status_code=200,
            headers={},
            content=b"test",
            url="https://example.com",
        )

        handler.reset_session()

        assert handler._last_response is None
        assert handler._cookie_store.get_for_url("https://example.com") == {}
        handler.close()

    def test_clear_cookies_all(self):
        """Test clear_cookies clears all cookies."""
        handler = HTTPHandler(persist_session=True)
        handler._cookie_store.set("cookie1", "value1", "example.com")
        handler._cookie_store.set("cookie2", "value2", "other.com")

        handler.clear_cookies()

        assert handler._cookie_store.get_for_url("https://example.com") == {}
        assert handler._cookie_store.get_for_url("https://other.com") == {}
        handler.close()

    def test_clear_cookies_specific_domain(self):
        """Test clear_cookies clears only specified domain."""
        handler = HTTPHandler(persist_session=True)
        handler._cookie_store.set("cookie1", "value1", "example.com")
        handler._cookie_store.set("cookie2", "value2", "other.com")

        handler.clear_cookies("example.com")

        assert handler._cookie_store.get_for_url("https://example.com") == {}
        assert handler._cookie_store.get_for_url("https://other.com") == {"cookie2": "value2"}
        handler.close()


class TestHTTPHandlerHeaderManagement:
    """Tests for header management methods."""

    def test_set_headers(self):
        """Test set_headers sets default headers."""
        handler = HTTPHandler()
        handler.set_headers({"User-Agent": "Test/1.0", "Accept": "application/json"})

        assert handler._default_headers == {
            "User-Agent": "Test/1.0",
            "Accept": "application/json",
        }
        handler.close()

    def test_get_default_headers(self):
        """Test get_default_headers returns current defaults."""
        handler = HTTPHandler(headers={"User-Agent": "Test/1.0"})
        headers = handler.get_default_headers()

        assert headers == {"User-Agent": "Test/1.0"}
        # Ensure it returns a copy
        headers["New-Header"] = "value"
        assert "New-Header" not in handler._default_headers
        handler.close()

    def test_clear_headers(self):
        """Test clear_headers removes all default headers."""
        handler = HTTPHandler(headers={"User-Agent": "Test/1.0"})
        handler.clear_headers()

        assert handler._default_headers == {}
        handler.close()

    def test_add_header(self):
        """Test add_header adds a single header."""
        handler = HTTPHandler()
        handler.add_header("Authorization", "Bearer token123")

        assert handler._default_headers == {"Authorization": "Bearer token123"}
        handler.close()

    def test_remove_header(self):
        """Test remove_header removes a header."""
        handler = HTTPHandler(headers={"User-Agent": "Test/1.0", "Accept": "*/*"})
        handler.remove_header("Accept")

        assert handler._default_headers == {"User-Agent": "Test/1.0"}
        handler.close()

    def test_remove_nonexistent_header(self):
        """Test remove_header does nothing for nonexistent header."""
        handler = HTTPHandler(headers={"User-Agent": "Test/1.0"})
        handler.remove_header("NonExistent")  # Should not raise

        assert handler._default_headers == {"User-Agent": "Test/1.0"}
        handler.close()


class TestHTTPHandlerProxyControl:
    """Tests for proxy control methods."""

    def test_set_proxy(self):
        """Test set_proxy configures proxy."""
        handler = HTTPHandler()
        handler.set_proxy("socks5://localhost:1080")

        assert handler._proxy == "socks5://localhost:1080"
        assert handler._proxy_enabled is True
        handler.close()

    def test_set_proxy_none_clears(self):
        """Test set_proxy(None) clears proxy."""
        handler = HTTPHandler(proxy="socks5://localhost:1080")
        handler.set_proxy(None)

        assert handler._proxy is None
        assert handler._proxy_enabled is False
        handler.close()

    def test_enable_proxy(self):
        """Test enable_proxy enables configured proxy."""
        handler = HTTPHandler(proxy="socks5://localhost:1080")
        handler.disable_proxy()
        assert handler.proxy_enabled is False

        handler.enable_proxy()
        assert handler.proxy_enabled is True
        handler.close()

    def test_disable_proxy(self):
        """Test disable_proxy temporarily disables proxy."""
        handler = HTTPHandler(proxy="socks5://localhost:1080")
        assert handler.proxy_enabled is True

        handler.disable_proxy()
        assert handler.proxy_enabled is False
        assert handler._proxy == "socks5://localhost:1080"  # Still configured
        handler.close()

    def test_proxy_enabled_property(self):
        """Test proxy_enabled property."""
        handler = HTTPHandler()
        assert handler.proxy_enabled is False

        handler.set_proxy("socks5://localhost:1080")
        assert handler.proxy_enabled is True

        handler.disable_proxy()
        assert handler.proxy_enabled is False
        handler.close()

    def test_proxy_property(self):
        """Test proxy property returns configured proxy."""
        handler = HTTPHandler(proxy="socks5://localhost:1080")
        assert handler.proxy == "socks5://localhost:1080"
        handler.close()


class TestHTTPHandlerContextManagers:
    """Tests for context manager support."""

    def test_enter_exit(self):
        """Test __enter__ and __exit__."""
        with HTTPHandler() as handler:
            assert isinstance(handler, HTTPHandler)
            assert handler._closed is False
        assert handler._closed is True

    def test_session_context_manager(self):
        """Test session() context manager."""
        handler = HTTPHandler(persist_session=False)

        with handler.session() as session:
            assert session.persist_session is True
            # Can use session for requests within this scope

        # After exiting, persist_session should be back to False
        assert handler.persist_session is False
        handler.close()

    def test_session_context_manager_auto_resets(self):
        """Test session() context manager resets on exit."""
        handler = HTTPHandler(persist_session=True)
        handler._cookie_store.set("original", "value", "example.com")

        with handler.session() as session:
            session._cookie_store.set("new_cookie", "new_value", "example.com")

        # Original cookies should be restored after context exit
        cookies = handler._cookie_store.get_for_url("https://example.com")
        assert cookies == {"original": "value"}
        handler.close()


class TestHTTPHandlerWarnings:
    """Tests for warning behavior."""

    def test_warning_when_no_headers(self):
        """Test warning is issued when no headers provided."""
        handler = HTTPHandler()

        with patch.object(handler._transport, 'request_sync') as mock_request:
            mock_request.return_value = Response(
                status_code=200,
                headers={},
                content=b"test",
                url="https://example.com",
            )

            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                handler.get("https://example.com")

                assert len(w) == 1
                assert "No headers provided" in str(w[0].message)
                assert issubclass(w[0].category, UserWarning)

        handler.close()

    def test_no_warning_when_headers_provided(self):
        """Test no warning when headers are provided."""
        handler = HTTPHandler()

        with patch.object(handler._transport, 'request_sync') as mock_request:
            mock_request.return_value = Response(
                status_code=200,
                headers={},
                content=b"test",
                url="https://example.com",
            )

            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                handler.get("https://example.com", headers={"User-Agent": "Test/1.0"})

                # No warning should be issued
                assert len(w) == 0

        handler.close()

    def test_no_warning_when_default_headers_set(self):
        """Test no warning when default headers are set."""
        handler = HTTPHandler(headers={"User-Agent": "Test/1.0"})

        with patch.object(handler._transport, 'request_sync') as mock_request:
            mock_request.return_value = Response(
                status_code=200,
                headers={},
                content=b"test",
                url="https://example.com",
            )

            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                handler.get("https://example.com")

                # No warning should be issued
                assert len(w) == 0

        handler.close()


class TestHTTPHandlerHTTPMethods:
    """Tests for HTTP method shortcuts."""

    def setup_method(self):
        """Setup handler with mocked transport."""
        self.handler = HTTPHandler(headers={"User-Agent": "Test/1.0"})
        self.mock_response = Response(
            status_code=200,
            headers={"Content-Type": "application/json"},
            content=b'{"key": "value"}',
            url="https://example.com",
            elapsed=0.1,
        )

    def teardown_method(self):
        """Cleanup handler."""
        self.handler.close()

    def test_get_method(self):
        """Test GET request."""
        with patch.object(self.handler._transport, 'request_sync') as mock_request:
            mock_request.return_value = self.mock_response
            response = self.handler.get("https://example.com")

            mock_request.assert_called_once()
            call_args = mock_request.call_args
            assert call_args.kwargs["request"].method == "GET"
            assert response.status_code == 200

    def test_post_method(self):
        """Test POST request."""
        with patch.object(self.handler._transport, 'request_sync') as mock_request:
            mock_request.return_value = self.mock_response
            response = self.handler.post(
                "https://example.com",
                json={"data": "test"},
            )

            mock_request.assert_called_once()
            call_args = mock_request.call_args
            assert call_args.kwargs["request"].method == "POST"
            assert call_args.kwargs["request"].json == {"data": "test"}

    def test_put_method(self):
        """Test PUT request."""
        with patch.object(self.handler._transport, 'request_sync') as mock_request:
            mock_request.return_value = self.mock_response
            response = self.handler.put(
                "https://example.com",
                data={"key": "value"},
            )

            mock_request.assert_called_once()
            call_args = mock_request.call_args
            assert call_args.kwargs["request"].method == "PUT"

    def test_delete_method(self):
        """Test DELETE request."""
        with patch.object(self.handler._transport, 'request_sync') as mock_request:
            mock_request.return_value = self.mock_response
            response = self.handler.delete("https://example.com")

            mock_request.assert_called_once()
            call_args = mock_request.call_args
            assert call_args.kwargs["request"].method == "DELETE"

    def test_patch_method(self):
        """Test PATCH request."""
        with patch.object(self.handler._transport, 'request_sync') as mock_request:
            mock_request.return_value = self.mock_response
            response = self.handler.patch(
                "https://example.com",
                json={"partial": "update"},
            )

            mock_request.assert_called_once()
            call_args = mock_request.call_args
            assert call_args.kwargs["request"].method == "PATCH"

    def test_head_method(self):
        """Test HEAD request."""
        with patch.object(self.handler._transport, 'request_sync') as mock_request:
            mock_request.return_value = self.mock_response
            response = self.handler.head("https://example.com")

            mock_request.assert_called_once()
            call_args = mock_request.call_args
            assert call_args.kwargs["request"].method == "HEAD"

    def test_options_method(self):
        """Test OPTIONS request."""
        with patch.object(self.handler._transport, 'request_sync') as mock_request:
            mock_request.return_value = self.mock_response
            response = self.handler.options("https://example.com")

            mock_request.assert_called_once()
            call_args = mock_request.call_args
            assert call_args.kwargs["request"].method == "OPTIONS"


class TestHTTPHandlerStreaming:
    """Tests for streaming support."""

    def test_stream_yields_chunks(self):
        """Test stream yields content in chunks."""
        handler = HTTPHandler(headers={"User-Agent": "Test/1.0"})

        with patch.object(handler._transport, 'request_sync') as mock_request:
            mock_request.return_value = Response(
                status_code=200,
                headers={},
                content=b"0123456789",
                url="https://example.com",
            )

            chunks = list(handler.stream("https://example.com", chunk_size=3))

            assert chunks == [b"012", b"345", b"678", b"9"]

        handler.close()

    def test_stream_with_callback(self):
        """Test stream calls callback with progress."""
        handler = HTTPHandler(headers={"User-Agent": "Test/1.0"})
        progress_calls = []

        def progress_callback(chunk, total, length):
            progress_calls.append((len(chunk), total, length))

        with patch.object(handler._transport, 'request_sync') as mock_request:
            mock_request.return_value = Response(
                status_code=200,
                headers={},
                content=b"0123456789",
                url="https://example.com",
            )

            list(handler.stream(
                "https://example.com",
                chunk_size=3,
                callback=progress_callback,
            ))

            assert progress_calls == [
                (3, 3, 10),
                (3, 6, 10),
                (3, 9, 10),
                (1, 10, 10),
            ]

        handler.close()


class TestHTTPHandlerClosed:
    """Tests for closed handler behavior."""

    def test_request_after_close_raises(self):
        """Test request after close raises error."""
        handler = HTTPHandler()
        handler.close()

        with pytest.raises(Exception) as exc_info:
            handler.get("https://example.com")

        assert "closed" in str(exc_info.value).lower()

    def test_double_close_safe(self):
        """Test closing twice is safe."""
        handler = HTTPHandler()
        handler.close()
        handler.close()  # Should not raise


class TestNoResponseError:
    """Tests for NoResponseError exception."""

    def test_error_message(self):
        """Test error has appropriate message."""
        error = NoResponseError()
        assert "No response available" in str(error)
        assert "Make a request first" in str(error)
