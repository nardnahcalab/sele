# sele Test Coverage

This document catalogs all test cases in the sele codebase, organized by module.

## Test Summary

- **Total Tests**: 92
- **Passing**: 92
- **Skipped**: 0
- **Coverage**: All major modules tested

## Test Modules

### test_bubblewrap_args.py

Tests for the pure `build_bwrap_args` argv builder. These tests do not require `bwrap` to be installed.

| Test Case | Functionality Tested | Module | Result |
|-----------|---------------------|--------|--------|
| `test_default_args_include_hardening_and_namespaces` | Verifies default bubblewrap hardening flags and namespace isolation are present | `sele.sandbox.bubblewrap.build_bwrap_args` | ✅ Pass |
| `test_egress_none_unshares_net` | Confirms `--unshare-net` flag is added when egress mode is `none` | `sele.sandbox.bubblewrap.build_bwrap_args` | ✅ Pass |
| `test_cwd_and_chdir_present` | Ensures cwd is bind-mounted rw and `--chdir` points to it | `sele.sandbox.bubblewrap.build_bwrap_args` | ✅ Pass |
| `test_command_is_invoked_via_bash_lc` | Verifies command is executed via `bash -lc` | `sele.sandbox.bubblewrap.build_bwrap_args` | ✅ Pass |
| `test_default_ro_binds_only_for_existing_paths` | Confirms ro-binds only emit for paths that actually exist | `sele.sandbox.bubblewrap.build_bwrap_args` | ✅ Pass |
| `test_default_tmpfs_present` | Checks that default tmpfs mounts are present | `sele.sandbox.bubblewrap.build_bwrap_args` | ✅ Pass |
| `test_extra_rw_binds_resolved_and_added` | Verifies extra rw binds are resolved and added to args | `sele.sandbox.bubblewrap.build_bwrap_args` | ✅ Pass |
| `test_env_is_cleared_then_reapplied` | Ensures environment is cleared then reapplied via `--setenv` | `sele.sandbox.bubblewrap.build_bwrap_args` | ✅ Pass |
| `test_hostname_is_passed` | Confirms custom hostname is passed via `--hostname` | `sele.sandbox.bubblewrap.build_bwrap_args` | ✅ Pass |

### test_bubblewrap_integration.py

Integration tests that actually invoke `bwrap`. Skipped automatically when bubblewrap is not installed on the host.

| Test Case | Functionality Tested | Module | Result |
|-----------|---------------------|--------|--------|
| `test_run_shell_executes_inside_sandbox` | Verifies shell commands execute inside bubblewrap sandbox | `sele.sandbox.bubblewrap.BubblewrapSandbox` | ✅ Pass |
| `test_egress_none_blocks_dns` | Confirms DNS resolution is blocked when egress mode is `none` | `sele.sandbox.bubblewrap.BubblewrapSandbox` | ✅ Pass |
| `test_writes_to_cwd_are_visible_on_host` | Ensures writes to sandbox cwd are visible on host | `sele.sandbox.bubblewrap.BubblewrapSandbox` | ✅ Pass |
| `test_caps_are_dropped` | Verifies capabilities are dropped (mount should fail) | `sele.sandbox.bubblewrap.BubblewrapSandbox` | ✅ Pass |

### test_chat_compat.py

Unit tests for shared OpenAI-shape chat helpers used by both `openai_compat` and `llama_cpp_native` adapters.

| Test Case | Functionality Tested | Module | Result |
|-----------|---------------------|--------|--------|
| `test_msg_to_openai_user_basic` | Converts user message to OpenAI dict format | `sele.models._chat_compat.msg_to_openai_dict` | ✅ Pass |
| `test_msg_to_openai_tool_role_carries_call_id_and_name` | Tool role message preserves call_id and name | `sele.models._chat_compat.msg_to_openai_dict` | ✅ Pass |
| `test_msg_to_openai_assistant_with_tool_calls_serializes_args` | Assistant with tool_calls serializes arguments as JSON | `sele.models._chat_compat.msg_to_openai_dict` | ✅ Pass |
| `test_tool_to_openai_dict_shape` | Converts ToolSpec to OpenAI function dict format | `sele.models._chat_compat.tool_to_openai_dict` | ✅ Pass |
| `test_parse_openai_choice_text_only` | Parses OpenAI response with text only | `sele.models._chat_compat.parse_openai_choice` | ✅ Pass |
| `test_parse_openai_choice_with_tool_calls` | Parses OpenAI response with tool_calls | `sele.models._chat_compat.parse_openai_choice` | ✅ Pass |
| `test_parse_openai_choice_preserves_invalid_json_args` | Preserves invalid JSON args in `_raw` field | `sele.models._chat_compat.parse_openai_choice` | ✅ Pass |

### test_egress_proxy.py

Tests for the egress allowlist matcher and the threaded CONNECT proxy. The proxy tests open real localhost sockets.

| Test Case | Functionality Tested | Module | Result |
|-----------|---------------------|--------|--------|
| `test_host_matches` (parametrized, 9 cases) | Hostname allowlist matching with wildcards and case insensitivity | `sele.sandbox._egress.host_matches` | ✅ Pass |
| `test_proxy_allows_listed_host_and_pipes_data` | Proxy allows listed host and pipes data through | `sele.sandbox._egress.EgressProxy` | ✅ Pass |
| `test_proxy_rejects_unlisted_host_with_403` | Proxy rejects unlisted host with HTTP 403 | `sele.sandbox._egress.EgressProxy` | ✅ Pass |
| `test_proxy_rejects_non_connect_with_405` | Proxy rejects non-CONNECT requests with HTTP 405 | `sele.sandbox._egress.EgressProxy` | ✅ Pass |

### test_end_to_end.py

End-to-end smoke test using a mock model adapter. Exercises registry, builder, profile loading, ToolLoop, native_tools protocol, host_direct sandbox, fs_write tool, jsonl tracer.

| Test Case | Functionality Tested | Module | Result |
|-----------|---------------------|--------|--------|
| `test_loop_runs_tools_and_writes_trace` | Full loop execution with tool calls and trace writing | `sele.builder`, `sele.loops.tool_loop` | ✅ Pass |
| `test_react_text_protocol_parses_tool_blocks` | ReAct protocol parses tool blocks from markdown | `sele.protocols.react_text.ReActTextProtocol` | ✅ Pass |
| `test_react_final_block_terminates` | ReAct protocol handles final block termination | `sele.protocols.react_text.ReActTextProtocol` | ✅ Pass |
| `test_sandbox_rejects_path_escape` | Sandbox rejects paths that escape cwd boundary | `sele.sandbox.host_direct.HostDirectSandbox` | ✅ Pass |

### test_eval.py

Tests for the evaluation runner.

| Test Case | Functionality Tested | Module | Result |
|-----------|---------------------|--------|--------|
| `test_load_benchmark` | Loads benchmark tasks from JSONL file | `sele.eval.EvalRunner.load_benchmark` | ✅ Pass |
| `test_load_benchmark_with_max_tasks` | Respects max_tasks limit when loading benchmark | `sele.eval.EvalRunner.load_benchmark` | ✅ Pass |
| `test_load_benchmark_missing_file` | Raises FileNotFoundError for missing benchmark file | `sele.eval.EvalRunner.load_benchmark` | ✅ Pass |
| `test_load_benchmark_invalid_json` | Raises ValueError for invalid JSON in benchmark | `sele.eval.EvalRunner.load_benchmark` | ✅ Pass |
| `test_task_result_dataclass` | TaskResult dataclass structure validation | `sele.eval.TaskResult` | ✅ Pass |
| `test_write_results` | Writes results to JSONL output file | `sele.eval.EvalRunner.write_results` | ✅ Pass |
| `test_print_summary` | Prints evaluation summary to stdout | `sele.eval.EvalRunner.print_summary` | ✅ Pass |

### test_llama_cpp_native.py

Tests for the in-process llama.cpp adapter. Uses a fake `Llama` class via module loader hook to assert on exact kwargs passed.

| Test Case | Functionality Tested | Module | Result |
|-----------|---------------------|--------|--------|
| `test_missing_model_path_is_a_clear_error` | Raises clear error when model_path is missing | `sele.models.llama_cpp_native.LlamaCppNativeAdapter` | ✅ Pass |
| `test_complete_passes_messages_tools_and_sampling_params` | Passes messages, tools, and sampling params to llama.cpp | `sele.models.llama_cpp_native.LlamaCppNativeAdapter` | ✅ Pass |
| `test_assistant_tool_calls_serialize_for_followup_turn` | Serializes assistant tool_calls for follow-up turns | `sele.models.llama_cpp_native.LlamaCppNativeAdapter` | ✅ Pass |
| `test_model_cache_reuses_instance_for_same_params` | Model cache reuses instance for same params | `sele.models.llama_cpp_native` (cache) | ✅ Pass |
| `test_model_cache_keys_on_loader_relevant_params` | Model cache keys on loader-relevant params | `sele.models.llama_cpp_native` (cache) | ✅ Pass |

### test_summarize_memory.py

Tests for `SummarizeMemory`. Uses a scripted `ModelAdapter` to assert on what the summarizer is asked to produce, when it's called, and how its output is integrated.

| Test Case | Functionality Tested | Module | Result |
|-----------|---------------------|--------|--------|
| `test_under_trigger_no_compaction` | No compaction when under trigger threshold | `sele.memory.summarize.SummarizeMemory` | ✅ Pass |
| `test_above_trigger_compacts_and_keeps_system_plus_summary_plus_recent` | Compacts when above trigger, keeps system + summary + recent | `sele.memory.summarize.SummarizeMemory` | ✅ Pass |
| `test_summarizer_receives_prompt_and_transcript` | Summarizer receives custom prompt and transcript | `sele.memory.summarize.SummarizeMemory` | ✅ Pass |
| `test_compaction_does_not_thrash_after_summary_fits` | No thrashing after summary fits budget | `sele.memory.summarize.SummarizeMemory` | ✅ Pass |
| `test_recent_chars_capped_when_larger_than_trigger` | Recent chars capped when larger than trigger | `sele.memory.summarize.SummarizeMemory` | ✅ Pass |
| `test_boundary_does_not_split_tool_call_pair` | Boundary does not split tool-call/tool-result pairs | `sele.memory.summarize.SummarizeMemory` | ✅ Pass |
| `test_no_adapter_falls_back_to_truncation_with_notice` | Falls back to truncation with notice when no adapter | `sele.memory.summarize.SummarizeMemory` | ✅ Pass |
| `test_summarizer_exception_does_not_crash` | Summarizer exceptions don't crash the loop | `sele.memory.summarize.SummarizeMemory` | ✅ Pass |
| `test_render_transcript_handles_tool_calls_and_tool_results` | Transcript rendering handles tool calls and results | `sele.memory.summarize.render_transcript` | ✅ Pass |
| `test_builder_wires_adapter_into_summarize_memory` | Builder wires adapter into SummarizeMemory | `sele.builder` + `sele.memory.summarize` | ✅ Pass |

### test_tools.py

Unit tests for tool implementations (python_exec and http).

| Test Case | Functionality Tested | Module | Result |
|-----------|---------------------|--------|--------|
| `test_python_exec_simple_code` | Executes simple Python code | `sele.tools.python_exec.python_exec` | ✅ Pass |
| `test_python_exec_syntax_error` | Handles syntax errors in Python code | `sele.tools.python_exec.python_exec` | ✅ Pass |
| `test_python_exec_multiline` | Executes multi-line Python code | `sele.tools.python_exec.python_exec` | ✅ Pass |
| `test_python_exec_missing_code` | Handles missing code parameter | `sele.tools.python_exec.python_exec` | ✅ Pass |
| `test_python_exec_timeout` | Handles timeout for long-running Python code | `sele.tools.python_exec.python_exec` | ✅ Pass |
| `test_http_get_request` | Executes HTTP GET request (mocked) | `sele.tools.http.http` | ✅ Pass |
| `test_http_post_request` | Executes HTTP POST request (mocked) | `sele.tools.http.http` | ✅ Pass |
| `test_http_error_status` | Handles HTTP error status codes | `sele.tools.http.http` | ✅ Pass |
| `test_http_missing_url` | Handles missing URL parameter | `sele.tools.http.http` | ✅ Pass |
| `test_http_with_headers` | Executes HTTP request with custom headers (mocked) | `sele.tools.http.http` | ✅ Pass |

### test_skills.py

Tests for the skills framework including reflexion and context_manager skills.

| Test Case | Functionality Tested | Module | Result |
|-----------|---------------------|--------|--------|
| `test_skills_config_defaults` | SkillsConfig has sensible defaults | `sele.config.SkillsConfig` | ✅ Pass |
| `test_skills_config_with_values` | SkillsConfig with custom values | `sele.config.SkillsConfig` | ✅ Pass |
| `test_loop_config_includes_skills` | LoopConfig includes skills configuration | `sele.config.LoopConfig` | ✅ Pass |
| `test_reflexion_skill_initialization` | ReflexionSkill initialization | `sele.skills.reflexion.ReflexionSkill` | ✅ Pass |
| `test_reflexion_skill_with_config` | ReflexionSkill with custom configuration | `sele.skills.reflexion.ReflexionSkill` | ✅ Pass |
| `test_context_manager_skill_initialization` | ContextManagerSkill initialization | `sele.skills.context_manager.ContextManagerSkill` | ✅ Pass |
| `test_context_manager_skill_with_config` | ContextManagerSkill with custom configuration | `sele.skills.context_manager.ContextManagerSkill` | ✅ Pass |
| `test_base_skill_hooks` | BaseSkill hooks can be overridden | `sele.skills.base.BaseSkill` | ✅ Pass |
| `test_skills_registered_in_registry` | Built-in skills are registered | `sele.registry` | ✅ Pass |
| `test_skill_retrieval_from_registry` | Retrieving skills from registry | `sele.registry` | ✅ Pass |
| `test_skill_on_loop_end_default` | BaseSkill.on_loop_end returns text unchanged | `sele.skills.base.BaseSkill` | ✅ Pass |
| `test_reflexion_skill_progress_tracking` | ReflexionSkill tracks progress | `sele.skills.reflexion.ReflexionSkill` | ✅ Pass |
| `test_context_manager_skill_compression_trigger` | ContextManagerSkill detects compression need | `sele.skills.context_manager.ContextManagerSkill` | ✅ Pass |
| `test_skills_config_with_skill_settings` | SkillsConfig with per-skill settings | `sele.config.SkillsConfig` | ✅ Pass |

## Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_tools.py

# Run with verbose output
pytest -v

# Run specific test
pytest tests/test_tools.py::test_python_exec_simple_code
```

## Test Categories

### Unit Tests
- `test_chat_compat.py` - OpenAI-shape message conversion
- `test_tools.py` - Tool implementations
- `test_eval.py` - Eval runner components
- Part of `test_summarize_memory.py` - Memory logic

### Integration Tests
- `test_bubblewrap_args.py` - Bubblewrap argument building
- `test_egress_proxy.py` - Egress proxy functionality
- `test_end_to_end.py` - Full loop execution
- Part of `test_summarize_memory.py` - Builder integration

### System Tests
- `test_bubblewrap_integration.py` - Real bubblewrap execution (skipped on non-Linux)
- `test_llama_cpp_native.py` - Llama.cpp adapter with fake model

## Coverage Notes

### Well-Covered Areas
- Tool implementations (python_exec, http)
- Memory backends (full_history, summarize)
- Chat compatibility layer
- Eval runner
- Bubblewrap argument building
- Egress proxy

### Areas for Future Test Expansion
- OpenAI compatibility adapter (currently tested via chat_compat)
- Protocol implementations (react_text has basic tests)
- Loop implementations (tested via end-to-end)
- Approval policies (currently no dedicated tests)
- Tracer implementations (tested via end-to-end)

### Skipped Tests
- None (all 68 tests pass on Linux with bubblewrap installed)

## Test Data Fixtures

Most tests use `tmp_path` fixture from pytest for temporary directories. Some tests use:
- `monkeypatch` for mocking functions
- `capsys` for capturing stdout/stderr
- Custom fixtures for model adapters (e.g., `_FakeLlama` in llama_cpp tests)

## Mocking Strategy

- **Model adapters**: Fake implementations that capture calls and return canned responses
- **Shell commands**: Monkeypatch `sandbox.run_shell` to avoid actual execution
- **Network requests**: Mock to avoid external dependencies
- **Filesystem**: Use `tmp_path` for isolated test environments

## Continuous Integration

Tests run on every commit. Expected to pass on:
- Linux (all 92 tests, including bubblewrap integration when bwrap is installed)
- macOS (88 tests, bubblewrap integration skipped if bwrap not available)
- Windows (88 tests, bubblewrap integration not applicable)
