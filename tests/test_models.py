"""Tests for Request and Response models."""

import json

import pytest

from http_client import (
    Request,
    Response,
    BatchResult,
    HTTPClientError,
    HTTPError,
    TransportError,
    RateLimitExceeded,
    AllProxiesFailed,
    MaxRetriesExceeded,
)


class TestRequest:
    """Tests for Request dataclass."""

    def test_basic_request(self):
        """Test basic request creation."""
        request = Request(method="GET", url="https://example.com")

        assert request.method == "GET"
        assert request.url == "https://example.com"
        assert request.headers == {}
        assert request.params is None
        assert request.data is None
        assert request.json is None
        assert request.cookies is None
        assert request.timeout is None
        assert request.proxy is None

    def test_method_normalized_to_uppercase(self):
        """Test that method is normalized to uppercase."""
        request = Request(method="get", url="https://example.com")
        assert request.method == "GET"

        request = Request(method="Post", url="https://example.com")
        assert request.method == "POST"

    def test_request_with_all_options(self):
        """Test request with all options set."""
        request = Request(
            method="POST",
            url="https://example.com/api",
            headers={"Content-Type": "application/json"},
            params={"page": "1"},
            json={"key": "value"},
            cookies={"session": "abc"},
            timeout=10.0,
            proxy="http://proxy:8080",
        )

        assert request.method == "POST"
        assert request.headers == {"Content-Type": "application/json"}
        assert request.params == {"page": "1"}
        assert request.json == {"key": "value"}
        assert request.cookies == {"session": "abc"}
        assert request.timeout == 10.0
        assert request.proxy == "http://proxy:8080"

    def test_request_with_form_data(self):
        """Test request with form data."""
        request = Request(
            method="POST",
            url="https://example.com/form",
            data={"username": "user", "password": "pass"},
        )

        assert request.data == {"username": "user", "password": "pass"}

    def test_request_with_bytes_data(self):
        """Test request with bytes data."""
        request = Request(
            method="POST",
            url="https://example.com/upload",
            data=b"binary data",
        )

        assert request.data == b"binary data"


class TestResponse:
    """Tests for Response dataclass."""

    def test_basic_response(self):
        """Test basic response creation."""
        response = Response(
            status_code=200,
            headers={"Content-Type": "text/html"},
            content=b"<html>Hello</html>",
            url="https://example.com",
        )

        assert response.status_code == 200
        assert response.headers == {"Content-Type": "text/html"}
        assert response.content == b"<html>Hello</html>"
        assert response.url == "https://example.com"
        assert response.cookies == {}
        assert response.elapsed == 0.0
        assert response.request is None
        assert response.history == []

    def test_text_property(self):
        """Test text property decodes content."""
        response = Response(
            status_code=200,
            headers={},
            content=b"Hello World",
            url="https://example.com",
        )

        assert response.text == "Hello World"

    def test_text_property_unicode(self):
        """Test text property handles unicode."""
        response = Response(
            status_code=200,
            headers={},
            content="Héllo Wörld".encode("utf-8"),
            url="https://example.com",
        )

        assert response.text == "Héllo Wörld"

    def test_ok_property_success(self):
        """Test ok property for success status codes."""
        for status in [200, 201, 204, 299]:
            response = Response(
                status_code=status,
                headers={},
                content=b"",
                url="https://example.com",
            )
            assert response.ok is True

    def test_ok_property_failure(self):
        """Test ok property for failure status codes."""
        for status in [400, 401, 404, 500, 502, 503]:
            response = Response(
                status_code=status,
                headers={},
                content=b"",
                url="https://example.com",
            )
            assert response.ok is False

    def test_json_method(self):
        """Test JSON parsing method."""
        data = {"key": "value", "number": 42, "nested": {"a": 1}}
        response = Response(
            status_code=200,
            headers={"Content-Type": "application/json"},
            content=json.dumps(data).encode(),
            url="https://example.com",
        )

        assert response.json() == data

    def test_json_method_invalid(self):
        """Test JSON parsing with invalid content."""
        response = Response(
            status_code=200,
            headers={},
            content=b"not json",
            url="https://example.com",
        )

        with pytest.raises(json.JSONDecodeError):
            response.json()

    def test_raise_for_status_success(self):
        """Test raise_for_status with success status."""
        response = Response(
            status_code=200,
            headers={},
            content=b"OK",
            url="https://example.com",
        )

        # Should not raise
        response.raise_for_status()

    def test_raise_for_status_error(self):
        """Test raise_for_status with error status."""
        response = Response(
            status_code=404,
            headers={},
            content=b"Not Found",
            url="https://example.com/missing",
        )

        with pytest.raises(HTTPError) as exc_info:
            response.raise_for_status()

        assert exc_info.value.response == response
        assert "404" in str(exc_info.value)

    def test_response_with_cookies(self):
        """Test response with cookies."""
        response = Response(
            status_code=200,
            headers={},
            content=b"OK",
            url="https://example.com",
            cookies={"session": "abc123", "user": "test"},
        )

        assert response.cookies == {"session": "abc123", "user": "test"}

    def test_response_with_request(self):
        """Test response with attached request."""
        request = Request(method="GET", url="https://example.com")
        response = Response(
            status_code=200,
            headers={},
            content=b"OK",
            url="https://example.com",
            request=request,
        )

        assert response.request == request


class TestBatchResult:
    """Tests for BatchResult dataclass."""

    def test_all_success(self):
        """Test batch result with all successes."""
        responses = [
            Response(status_code=200, headers={}, content=b"1", url="url1"),
            Response(status_code=200, headers={}, content=b"2", url="url2"),
            Response(status_code=200, headers={}, content=b"3", url="url3"),
        ]

        result = BatchResult(responses=responses, errors={})

        assert result.success_count == 3
        assert result.failure_count == 0
        assert result.all_succeeded is True

    def test_partial_failure(self):
        """Test batch result with some failures."""
        responses = [
            Response(status_code=200, headers={}, content=b"1", url="url1"),
            None,
            Response(status_code=200, headers={}, content=b"3", url="url3"),
        ]
        errors = {1: TransportError("Connection failed")}

        result = BatchResult(responses=responses, errors=errors)

        assert result.success_count == 2
        assert result.failure_count == 1
        assert result.all_succeeded is False

    def test_all_failure(self):
        """Test batch result with all failures."""
        responses = [None, None, None]
        errors = {
            0: TransportError("Error 1"),
            1: TransportError("Error 2"),
            2: TransportError("Error 3"),
        }

        result = BatchResult(responses=responses, errors=errors)

        assert result.success_count == 0
        assert result.failure_count == 3
        assert result.all_succeeded is False

    def test_raise_on_error(self):
        """Test raise_on_error method."""
        error = TransportError("Connection failed")
        result = BatchResult(
            responses=[None],
            errors={0: error},
        )

        with pytest.raises(TransportError):
            result.raise_on_error()

    def test_raise_on_error_success(self):
        """Test raise_on_error with no errors."""
        result = BatchResult(
            responses=[Response(status_code=200, headers={}, content=b"", url="url")],
            errors={},
        )

        # Should not raise
        result.raise_on_error()


class TestExceptions:
    """Tests for custom exceptions."""

    def test_http_client_error(self):
        """Test base HTTPClientError."""
        error = HTTPClientError("Something went wrong")
        assert str(error) == "Something went wrong"

    def test_transport_error(self):
        """Test TransportError with original error."""
        original = ConnectionError("Connection refused")
        error = TransportError("Failed to connect", original_error=original)

        assert "Failed to connect" in str(error)
        assert error.original_error == original

    def test_http_error(self):
        """Test HTTPError with response."""
        response = Response(
            status_code=404,
            headers={},
            content=b"Not Found",
            url="https://example.com",
        )
        error = HTTPError("Not Found", response=response)

        assert error.response == response
        assert "Not Found" in str(error)

    def test_rate_limit_exceeded(self):
        """Test RateLimitExceeded."""
        error = RateLimitExceeded("example.com", retry_after=30.0)

        assert error.domain == "example.com"
        assert error.retry_after == 30.0
        assert "example.com" in str(error)
        assert "30" in str(error)

    def test_rate_limit_exceeded_no_retry(self):
        """Test RateLimitExceeded without retry_after."""
        error = RateLimitExceeded("example.com")

        assert error.domain == "example.com"
        assert error.retry_after is None

    def test_all_proxies_failed(self):
        """Test AllProxiesFailed."""
        error = AllProxiesFailed()
        assert "All proxies" in str(error)

    def test_max_retries_exceeded(self):
        """Test MaxRetriesExceeded."""
        last_error = TransportError("Connection failed")
        error = MaxRetriesExceeded(
            url="https://example.com",
            attempts=3,
            last_error=last_error,
        )

        assert error.url == "https://example.com"
        assert error.attempts == 3
        assert error.last_error == last_error
        assert "3" in str(error)
