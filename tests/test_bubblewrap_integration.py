"""Integration tests that actually invoke ``bwrap``.

Skipped automatically when bubblewrap is not installed on the host.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from sele.config import EgressConfig, SandboxConfig
from sele.sandbox.bubblewrap import BubblewrapSandbox

pytestmark = pytest.mark.skipif(
    shutil.which("bwrap") is None,
    reason="bwrap not installed; install bubblewrap to run these",
)


def test_run_shell_executes_inside_sandbox(tmp_path: Path) -> None:
    sandbox = BubblewrapSandbox(SandboxConfig(cwd=str(tmp_path), egress=EgressConfig(mode="none")))
    rc, stdout, stderr = sandbox.run_shell("echo hello && pwd")
    assert rc == 0, stderr
    assert "hello" in stdout
    # cwd inside the sandbox is the resolved cwd path.
    assert str(tmp_path) in stdout


def test_egress_none_blocks_dns(tmp_path: Path) -> None:
    sandbox = BubblewrapSandbox(SandboxConfig(cwd=str(tmp_path), egress=EgressConfig(mode="none")))
    rc, _stdout, _stderr = sandbox.run_shell(
        "getent hosts github.com >/dev/null 2>&1 && echo OK || echo BLOCKED"
    )
    assert rc == 0
    assert "BLOCKED" in _stdout


def test_writes_to_cwd_are_visible_on_host(tmp_path: Path) -> None:
    sandbox = BubblewrapSandbox(SandboxConfig(cwd=str(tmp_path), egress=EgressConfig(mode="none")))
    rc, _, stderr = sandbox.run_shell("echo content > out.txt")
    assert rc == 0, stderr
    assert (tmp_path / "out.txt").read_text().strip() == "content"


def test_caps_are_dropped(tmp_path: Path) -> None:
    sandbox = BubblewrapSandbox(SandboxConfig(cwd=str(tmp_path), egress=EgressConfig(mode="none")))
    # mount(8) without privileges should fail; verifies caps were dropped.
    rc, _stdout, stderr = sandbox.run_shell("mount -t tmpfs tmpfs /tmp 2>&1; true")
    # The command itself is wrapped in `; true` so rc==0; we look for an error in output.
    combined = (_stdout + stderr).lower()
    assert "permission denied" in combined or "operation not permitted" in combined or "must be" in combined
