"""Unit tests for tool implementations."""

from __future__ import annotations

from sele.config import SandboxConfig
from sele.sandbox.host_direct import HostDirectSandbox
from sele.tools.http import http
from sele.tools.python_exec import python_exec


def test_python_exec_simple_code(tmp_path) -> None:
    sandbox = HostDirectSandbox(SandboxConfig(cwd=str(tmp_path)))
    result = python_exec(sandbox, {"code": "print('hello')", "_call_id": "test1"})
    assert result.ok
    assert "hello" in result.content
    assert result.call_id == "test1"


def test_python_exec_syntax_error(tmp_path) -> None:
    sandbox = HostDirectSandbox(SandboxConfig(cwd=str(tmp_path)))
    result = python_exec(sandbox, {"code": "print('unclosed", "_call_id": "test2"})
    assert not result.ok
    assert "SyntaxError" in result.content or "non-zero exit" in result.error


def test_python_exec_multiline(tmp_path) -> None:
    sandbox = HostDirectSandbox(SandboxConfig(cwd=str(tmp_path)))
    code = """import math
x = math.sqrt(16)
print(f"sqrt(16) = {x}")
"""
    result = python_exec(sandbox, {"code": code, "_call_id": "test3"})
    assert result.ok
    assert "sqrt(16) = 4.0" in result.content


def test_python_exec_missing_code(tmp_path) -> None:
    sandbox = HostDirectSandbox(SandboxConfig(cwd=str(tmp_path)))
    result = python_exec(sandbox, {"_call_id": "test4"})
    assert not result.ok
    assert "missing or invalid 'code'" in result.error


def test_python_exec_timeout(tmp_path) -> None:
    sandbox = HostDirectSandbox(SandboxConfig(cwd=str(tmp_path)))
    # This should timeout quickly
    result = python_exec(sandbox, {"code": "import time; time.sleep(10)", "timeout": 0.1})
    assert not result.ok  # Should timeout


def test_http_get_request(tmp_path, monkeypatch) -> None:
    # Mock the shell to avoid actual HTTP requests
    def mock_run_shell(command, *, timeout=None):
        # Simulate a successful GET request
        return 0, "response body\n200", ""

    sandbox = HostDirectSandbox(SandboxConfig(cwd=str(tmp_path)))
    sandbox.run_shell = mock_run_shell

    result = http(sandbox, {"url": "http://example.com", "_call_id": "http1"})
    assert result.ok
    assert "200" in result.content
    assert "response body" in result.content


def test_http_post_request(tmp_path, monkeypatch) -> None:
    def mock_run_shell(command, *, timeout=None):
        return 0, "created\n201", ""

    sandbox = HostDirectSandbox(SandboxConfig(cwd=str(tmp_path)))
    sandbox.run_shell = mock_run_shell

    result = http(sandbox, {
        "url": "http://example.com/api",
        "method": "POST",
        "body": '{"key": "value"}',
        "_call_id": "http2"
    })
    assert result.ok
    assert "201" in result.content


def test_http_error_status(tmp_path, monkeypatch) -> None:
    def mock_run_shell(command, *, timeout=None):
        return 0, "not found\n404", ""

    sandbox = HostDirectSandbox(SandboxConfig(cwd=str(tmp_path)))
    sandbox.run_shell = mock_run_shell

    result = http(sandbox, {"url": "http://example.com/notfound", "_call_id": "http3"})
    assert not result.ok
    assert "404" in result.content
    assert "HTTP 404" in result.error


def test_http_missing_url(tmp_path) -> None:
    sandbox = HostDirectSandbox(SandboxConfig(cwd=str(tmp_path)))
    result = http(sandbox, {"_call_id": "http4"})
    assert not result.ok
    assert "missing or invalid 'url'" in result.error


def test_http_with_headers(tmp_path, monkeypatch) -> None:
    def mock_run_shell(command, *, timeout=None):
        # Check that headers were added
        assert "-H" in command
        assert "Authorization:" in command
        return 0, "authorized\n200", ""

    sandbox = HostDirectSandbox(SandboxConfig(cwd=str(tmp_path)))
    sandbox.run_shell = mock_run_shell

    result = http(sandbox, {
        "url": "http://example.com/api",
        "headers": {"Authorization": "Bearer token123"},
        "_call_id": "http5"
    })
    assert result.ok
