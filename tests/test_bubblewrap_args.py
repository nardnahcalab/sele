"""Tests for the pure ``build_bwrap_args`` argv builder.

These tests do not require ``bwrap`` to be installed.
"""

from __future__ import annotations

from pathlib import Path

from sele.config import EgressConfig, SandboxConfig
from sele.sandbox.bubblewrap import (
    DEFAULT_RO_BINDS,
    DEFAULT_TMPFS,
    build_bwrap_args,
)


def _build(tmp_path: Path, **overrides) -> list[str]:
    cfg = SandboxConfig(cwd=str(tmp_path), **overrides)
    return build_bwrap_args(
        bwrap_path="/usr/bin/bwrap",
        config=cfg,
        cwd=tmp_path,
        command="echo hi",
        env={"PATH": "/usr/bin", "HOME": "/tmp"},
    )


def test_default_args_include_hardening_and_namespaces(tmp_path: Path) -> None:
    args = _build(tmp_path)
    assert args[0] == "/usr/bin/bwrap"
    for flag in (
        "--die-with-parent",
        "--new-session",
        "--unshare-ipc",
        "--unshare-pid",
        "--unshare-uts",
        "--unshare-cgroup-try",
        "--cap-drop",
        "ALL",
        "--clearenv",
    ):
        assert flag in args, f"missing flag: {flag}"
    # Default egress is "all" (share net), so --unshare-net must NOT be present.
    assert "--unshare-net" not in args


def test_egress_none_unshares_net(tmp_path: Path) -> None:
    args = _build(tmp_path, egress=EgressConfig(mode="none"))
    assert "--unshare-net" in args


def test_cwd_and_chdir_present(tmp_path: Path) -> None:
    args = _build(tmp_path)
    cwd_str = str(tmp_path)
    # cwd is bind-mounted rw and we --chdir to it.
    assert _has_pair(args, "--bind", cwd_str, cwd_str)
    chdir_idx = args.index("--chdir")
    assert args[chdir_idx + 1] == cwd_str


def test_command_is_invoked_via_bash_lc(tmp_path: Path) -> None:
    args = _build(tmp_path)
    assert "--" in args
    sep = args.index("--")
    assert args[sep + 1 : sep + 4] == ["bash", "-lc", "echo hi"]


def test_default_ro_binds_only_for_existing_paths(tmp_path: Path) -> None:
    args = _build(tmp_path)
    # Every --ro-bind we emit should be for a path that actually exists.
    for i, tok in enumerate(args):
        if tok == "--ro-bind":
            src = args[i + 1]
            assert Path(src).exists(), f"emitted --ro-bind for missing path {src}"
    # And at least one of the standard system paths got bound.
    bound = {args[i + 1] for i, tok in enumerate(args) if tok == "--ro-bind"}
    assert bound & {p for p in DEFAULT_RO_BINDS if Path(p).exists()}


def test_default_tmpfs_present(tmp_path: Path) -> None:
    args = _build(tmp_path)
    tmpfs_paths = [args[i + 1] for i, tok in enumerate(args) if tok == "--tmpfs"]
    assert set(DEFAULT_TMPFS).issubset(set(tmpfs_paths))


def test_extra_rw_binds_resolved_and_added(tmp_path: Path) -> None:
    extra = tmp_path / "extra"
    extra.mkdir()
    args = _build(tmp_path, rw_binds=[str(extra)])
    assert _has_pair(args, "--bind", str(extra.resolve()), str(extra.resolve()))


def test_env_is_cleared_then_reapplied(tmp_path: Path) -> None:
    args = _build(tmp_path)
    clearenv_idx = args.index("--clearenv")
    # Each (--setenv, K, V) triple should appear AFTER --clearenv.
    setenv_indices = [i for i, tok in enumerate(args) if tok == "--setenv"]
    assert setenv_indices, "expected at least one --setenv"
    assert all(i > clearenv_idx for i in setenv_indices)


def test_hostname_is_passed(tmp_path: Path) -> None:
    args = _build(tmp_path, hostname="custom-host")
    hi = args.index("--hostname")
    assert args[hi + 1] == "custom-host"


def _has_pair(args: list[str], flag: str, a: str, b: str) -> bool:
    for i, tok in enumerate(args):
        if tok == flag and args[i + 1 : i + 3] == [a, b]:
            return True
    return False
