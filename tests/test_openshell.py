"""Unit tests for OpenShell sandbox.

Tests mock subprocess calls to avoid requiring Docker and openshell installation.
"""

from __future__ import annotations

import subprocess
from unittest.mock import Mock, patch

import pytest

from sele.config import SandboxConfig
from sele.sandbox.openshell import OpenShellSandbox


def test_find_openshell_not_installed(tmp_path) -> None:
    """Test that a clear error is raised when openshell is not found."""
    with patch("shutil.which", return_value=None):
        from sele.sandbox.openshell import find_openshell

        with pytest.raises(RuntimeError) as exc_info:
            find_openshell()
        assert "OpenShell is not installed" in str(exc_info.value)


def test_find_openshell_installed(tmp_path) -> None:
    """Test that openshell path is found when installed."""
    with patch("shutil.which", return_value="/usr/bin/openshell"):
        from sele.sandbox.openshell import find_openshell

        path = find_openshell()
        assert path == "/usr/bin/openshell"


def test_openshell_sandbox_init(tmp_path) -> None:
    """Test sandbox initialization."""
    with patch("shutil.which", return_value="/usr/bin/openshell"):
        with patch("subprocess.run", return_value=subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )):
            config = SandboxConfig(cwd=str(tmp_path))
            sandbox = OpenShellSandbox(config)

            assert sandbox.sandbox_name.startswith("sele-")
            assert len(sandbox.sandbox_name) == len("sele-") + 8  # 8 char hash
            assert sandbox.cwd == tmp_path.resolve()


def test_openshell_resolve_path(tmp_path) -> None:
    """Test path resolution rejects escapes."""
    with patch("shutil.which", return_value="/usr/bin/openshell"):
        with patch("subprocess.run", return_value=subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr="already exists"
        )):
            config = SandboxConfig(cwd=str(tmp_path))
            sandbox = OpenShellSandbox(config, _skip_create=True)

            # Valid path
            assert sandbox.resolve("file.txt") == str(tmp_path / "file.txt")

            # Path escape
            with pytest.raises(PermissionError):
                sandbox.resolve("../../etc/passwd")


def test_openshell_run_shell(tmp_path) -> None:
    """Test shell command execution."""
    with patch("shutil.which", return_value="/usr/bin/openshell"):
        exec_mock = Mock(return_value=subprocess.CompletedProcess(
            args=[], returncode=0, stdout="hello\n", stderr=""
        ))

        def mock_run(cmd_args, **kwargs):
            if "exec" in cmd_args:
                return exec_mock(cmd_args, **kwargs)
            return subprocess.CompletedProcess(cmd_args, returncode=0, stdout="", stderr="already exists")

        with patch("subprocess.run", side_effect=mock_run):
            config = SandboxConfig(cwd=str(tmp_path))
            sandbox = OpenShellSandbox(config, _skip_create=True)

            rc, stdout, stderr = sandbox.run_shell("echo hello")

            assert rc == 0
            assert stdout == "hello\n"
            assert stderr == ""


def test_openshell_run_shell_timeout(tmp_path) -> None:
    """Test shell command timeout."""
    with patch("shutil.which", return_value="/usr/bin/openshell"):
        def mock_run(cmd_args, **kwargs):
            if "exec" in cmd_args:
                raise subprocess.TimeoutExpired("cmd", 0.1)
            return subprocess.CompletedProcess(cmd_args, returncode=0, stdout="", stderr="already exists")

        with patch("subprocess.run", side_effect=mock_run):
            config = SandboxConfig(cwd=str(tmp_path))
            sandbox = OpenShellSandbox(config, _skip_create=True)

            rc, stdout, stderr = sandbox.run_shell("sleep 10", timeout=0.1)

            assert rc == -1
            assert "timed out" in stderr


def test_openshell_read_file(tmp_path) -> None:
    """Test file reading."""
    with patch("shutil.which", return_value="/usr/bin/openshell"):
        with patch("subprocess.run", return_value=subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr="already exists"
        )):
            config = SandboxConfig(cwd=str(tmp_path))
            sandbox = OpenShellSandbox(config, _skip_create=True)

            # Create a test file
            test_file = tmp_path / "test.txt"
            test_file.write_text("hello world")

            content = sandbox.read_file("test.txt")
            assert content == "hello world"


def test_openshell_write_file(tmp_path) -> None:
    """Test file writing."""
    with patch("shutil.which", return_value="/usr/bin/openshell"):
        with patch("subprocess.run", return_value=subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr="already exists"
        )):
            config = SandboxConfig(cwd=str(tmp_path))
            sandbox = OpenShellSandbox(config, _skip_create=True)

            n = sandbox.write_file("out.txt", "test content")
            assert n == 12
            assert (tmp_path / "out.txt").read_text() == "test content"


def test_openshell_write_file_creates_dirs(tmp_path) -> None:
    """Test that write_file creates parent directories."""
    with patch("shutil.which", return_value="/usr/bin/openshell"):
        with patch("subprocess.run", return_value=subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr="already exists"
        )):
            config = SandboxConfig(cwd=str(tmp_path))
            sandbox = OpenShellSandbox(config, _skip_create=True)

            sandbox.write_file("subdir/file.txt", "content")
            assert (tmp_path / "subdir" / "file.txt").read_text() == "content"


def test_openshell_custom_path(tmp_path) -> None:
    """Test custom openshell path from config."""
    with patch("subprocess.run", return_value=subprocess.CompletedProcess(
        args=[], returncode=0, stdout="", stderr="already exists"
    )):
        config = SandboxConfig(cwd=str(tmp_path), openshell_path="/custom/openshell")
        sandbox = OpenShellSandbox(config, _skip_create=True)

        assert sandbox.openshell_path == "/custom/openshell"


def test_openshell_cleanup(tmp_path) -> None:
    """Test sandbox cleanup."""
    with patch("shutil.which", return_value="/usr/bin/openshell"):
        delete_mock = Mock(return_value=subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        ))

        def mock_run(cmd_args, **kwargs):
            if "delete" in cmd_args:
                return delete_mock(cmd_args, **kwargs)
            return subprocess.CompletedProcess(cmd_args, returncode=0, stdout="", stderr="already exists")

        with patch("subprocess.run", side_effect=mock_run):
            config = SandboxConfig(cwd=str(tmp_path))
            sandbox = OpenShellSandbox(config, _skip_create=True)
            sandbox._sandbox_created = True

            sandbox.cleanup()

            assert delete_mock.called
            assert sandbox._sandbox_created is False
