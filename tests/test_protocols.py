"""Tests for protocol implementations."""

import json

from sele.protocols.native_tools import NativeToolsProtocol
from sele.protocols.react_text import ReActTextProtocol, _format_tools
from sele.types import Message, ModelResponse, ToolCall, ToolSpec


def test_native_tools_protocol_name():
    """NativeToolsProtocol should have correct name."""
    protocol = NativeToolsProtocol()
    assert protocol.name == "native_tools"


def test_native_tools_protocol_init():
    """NativeToolsProtocol should initialize without arguments."""
    protocol = NativeToolsProtocol()
    assert protocol is not None


def test_native_tools_render_system_passthrough():
    """NativeToolsProtocol should pass through system prompt unchanged."""
    protocol = NativeToolsProtocol()
    base = "You are a helpful assistant."
    tools = [
        ToolSpec(name="test", description="Test tool", parameters={}),
    ]
    result = protocol.render_system(base, tools)
    assert result == base


def test_native_tools_render_system_with_empty_tools():
    """NativeToolsProtocol should handle empty tools list."""
    protocol = NativeToolsProtocol()
    base = "You are a helpful assistant."
    result = protocol.render_system(base, [])
    assert result == base


def test_native_tools_prepare_request_passthrough():
    """NativeToolsProtocol should pass through messages and tools unchanged."""
    protocol = NativeToolsProtocol()
    messages = [Message(role="user", content="test")]
    tools = [ToolSpec(name="test", description="Test tool", parameters={})]
    result_messages, result_tools = protocol.prepare_request(messages, tools)
    assert result_messages == messages
    assert result_tools == tools


def test_native_tools_parse_response():
    """NativeToolsProtocol should extract content and tool calls from response."""
    protocol = NativeToolsProtocol()
    response = ModelResponse(
        content="test response",
        tool_calls=[
            ToolCall(id="call1", name="test_tool", arguments={"arg": "value"}),
        ],
    )
    content, calls = protocol.parse_response(response)
    assert content == "test response"
    assert len(calls) == 1
    assert calls[0].name == "test_tool"


def test_native_tools_parse_response_empty():
    """NativeToolsProtocol should handle empty response."""
    protocol = NativeToolsProtocol()
    response = ModelResponse(content="", tool_calls=[])
    content, calls = protocol.parse_response(response)
    assert content == ""
    assert len(calls) == 0


def test_native_tools_parse_response_with_content_only():
    """NativeToolsProtocol should handle response with content only."""
    protocol = NativeToolsProtocol()
    response = ModelResponse(content="just text", tool_calls=[])
    content, calls = protocol.parse_response(response)
    assert content == "just text"
    assert len(calls) == 0


def test_react_text_protocol_name():
    """ReActTextProtocol should have correct name."""
    protocol = ReActTextProtocol()
    assert protocol.name == "react_text"


def test_react_text_protocol_init():
    """ReActTextProtocol should initialize without arguments."""
    protocol = ReActTextProtocol()
    assert protocol is not None


def test_format_tools_single():
    """_format_tools should format a single tool."""
    tools = [
        ToolSpec(
            name="test_tool",
            description="A test tool",
            parameters={"type": "object", "properties": {"arg": {"type": "string"}}},
        ),
    ]
    result = _format_tools(tools)
    assert "test_tool" in result
    assert "A test tool" in result
    assert "parameters schema:" in result


def test_format_tools_multiple():
    """_format_tools should format multiple tools."""
    tools = [
        ToolSpec(name="tool1", description="First tool", parameters={}),
        ToolSpec(name="tool2", description="Second tool", parameters={}),
    ]
    result = _format_tools(tools)
    assert "tool1" in result
    assert "tool2" in result
    assert "First tool" in result
    assert "Second tool" in result


def test_format_tools_empty():
    """_format_tools should handle empty tools list."""
    result = _format_tools([])
    assert result == ""


def test_format_tools_complex_parameters():
    """_format_tools should format complex parameter schemas."""
    tools = [
        ToolSpec(
            name="complex_tool",
            description="Tool with complex params",
            parameters={
                "type": "object",
                "properties": {
                    "url": {"type": "string"},
                    "method": {"type": "string", "enum": ["GET", "POST"]},
                    "headers": {
                        "type": "object",
                        "properties": {"Auth": {"type": "string"}},
                    },
                },
                "required": ["url", "method"],
            },
        ),
    ]
    result = _format_tools(tools)
    assert "complex_tool" in result
    assert "url" in result
    assert "method" in result


def test_react_text_render_system():
    """ReActTextProtocol should render system prompt with tools."""
    protocol = ReActTextProtocol()
    base = "You are a helpful assistant."
    tools = [
        ToolSpec(name="test_tool", description="Test tool", parameters={}),
    ]
    result = protocol.render_system(base, tools)
    assert base in result
    assert "test_tool" in result
    assert "```final" in result


def test_react_text_render_system_empty_tools():
    """ReActTextProtocol should render system prompt with no tools."""
    protocol = ReActTextProtocol()
    base = "You are a helpful assistant."
    result = protocol.render_system(base, [])
    assert base in result
    assert "```final" in result


def test_react_text_prepare_request():
    """ReActTextProtocol should return messages but empty tools."""
    protocol = ReActTextProtocol()
    messages = [Message(role="user", content="test")]
    tools = [ToolSpec(name="test", description="Test tool", parameters={})]
    result_messages, result_tools = protocol.prepare_request(messages, tools)
    assert result_messages == messages
    assert result_tools == []  # Tools are embedded in system prompt


def test_react_text_parse_tool_block():
    """ReActTextProtocol should parse tool blocks."""
    protocol = ReActTextProtocol()
    response = ModelResponse(
        content='```tool\n{"name": "test_tool", "arguments": {"arg": "value"}}\n```',
        tool_calls=[],
    )
    content, calls = protocol.parse_response(response)
    assert len(calls) == 1
    assert calls[0].name == "test_tool"
    assert calls[0].arguments == {"arg": "value"}


def test_react_text_parse_multiple_tool_blocks():
    """ReActTextProtocol should parse multiple tool blocks."""
    protocol = ReActTextProtocol()
    response = ModelResponse(
        content='```tool\n{"name": "tool1", "arguments": {"arg": "value1"}}\n```\n```tool\n{"name": "tool2", "arguments": {"arg": "value2"}}\n```',
        tool_calls=[],
    )
    content, calls = protocol.parse_response(response)
    assert len(calls) == 2
    assert calls[0].name == "tool1"
    assert calls[1].name == "tool2"


def test_react_text_parse_final_block():
    """ReActTextProtocol should parse final block and return empty calls."""
    protocol = ReActTextProtocol()
    response = ModelResponse(
        content='```final\nThis is the final answer.\n```',
        tool_calls=[],
    )
    content, calls = protocol.parse_response(response)
    assert content == "This is the final answer."
    assert len(calls) == 0


def test_react_text_parse_final_wins_over_tools():
    """ReActTextProtocol should prioritize final block over tool blocks."""
    protocol = ReActTextProtocol()
    response = ModelResponse(
        content='```tool\n{"name": "tool1", "arguments": {}}\n```\n```final\nFinal answer.\n```',
        tool_calls=[],
    )
    content, calls = protocol.parse_response(response)
    assert content == "Final answer."
    assert len(calls) == 0


def test_react_text_parse_mixed_content():
    """ReActTextProtocol should handle mixed prose and tool blocks."""
    protocol = ReActTextProtocol()
    response = ModelResponse(
        content="I will check the file.\n```tool\n{\"name\": \"read\", \"arguments\": {\"path\": \"test.txt\"}}\n```\nDone.",
        tool_calls=[],
    )
    content, calls = protocol.parse_response(response)
    assert len(calls) == 1
    assert calls[0].name == "read"
    assert "I will check the file." in content
    assert "Done." in content


def test_react_text_parse_invalid_json():
    """ReActTextProtocol should skip invalid JSON in tool blocks."""
    protocol = ReActTextProtocol()
    response = ModelResponse(
        content='```tool\n{invalid json}\n```',
        tool_calls=[],
    )
    content, calls = protocol.parse_response(response)
    assert len(calls) == 0


def test_react_text_parse_missing_name():
    """ReActTextProtocol should skip tool blocks without name."""
    protocol = ReActTextProtocol()
    response = ModelResponse(
        content='```tool\n{"arguments": {"arg": "value"}}\n```',
        tool_calls=[],
    )
    content, calls = protocol.parse_response(response)
    assert len(calls) == 0


def test_react_text_parse_alternate_key_names():
    """ReActTextProtocol should support alternate key names (tool, args)."""
    protocol = ReActTextProtocol()
    response = ModelResponse(
        content='```tool\n{"tool": "test_tool", "args": {"arg": "value"}}\n```',
        tool_calls=[],
    )
    content, calls = protocol.parse_response(response)
    assert len(calls) == 1
    assert calls[0].name == "test_tool"
    assert calls[0].arguments == {"arg": "value"}


def test_react_text_parse_case_insensitive():
    """ReActTextProtocol should be case-insensitive for block tags."""
    protocol = ReActTextProtocol()
    response = ModelResponse(
        content='```TOOL\n{"name": "test", "arguments": {}}\n```',
        tool_calls=[],
    )
    content, calls = protocol.parse_response(response)
    assert len(calls) == 1


def test_react_text_parse_whitespace_handling():
    """ReActTextProtocol should handle whitespace in tool blocks."""
    protocol = ReActTextProtocol()
    response = ModelResponse(
        content='```  tool  \n  {"name": "test", "arguments": {}}  \n```',
        tool_calls=[],
    )
    content, calls = protocol.parse_response(response)
    assert len(calls) == 1


def test_react_text_parse_empty_response():
    """ReActTextProtocol should handle empty response."""
    protocol = ReActTextProtocol()
    response = ModelResponse(content="", tool_calls=[])
    content, calls = protocol.parse_response(response)
    assert content == ""
    assert len(calls) == 0


def test_react_text_parse_prose_only():
    """ReActTextProtocol should handle prose without blocks."""
    protocol = ReActTextProtocol()
    response = ModelResponse(content="Just some text.", tool_calls=[])
    content, calls = protocol.parse_response(response)
    assert content == "Just some text."
    assert len(calls) == 0


def test_react_text_strips_tool_blocks_from_content():
    """ReActTextProtocol should remove tool blocks from returned content."""
    protocol = ReActTextProtocol()
    response = ModelResponse(
        content="Before.\n```tool\n{\"name\": \"test\", \"arguments\": {}}\n```\nAfter.",
        tool_calls=[],
    )
    content, calls = protocol.parse_response(response)
    assert "Before." in content
    assert "After." in content
    assert "```tool" not in content
    assert len(calls) == 1


def test_react_text_tool_call_id_format():
    """ReActTextProtocol should generate unique call IDs."""
    protocol = ReActTextProtocol()
    response = ModelResponse(
        content='```tool\n{"name": "test", "arguments": {}}\n```',
        tool_calls=[],
    )
    content, calls = protocol.parse_response(response)
    assert len(calls) == 1
    assert calls[0].id.startswith("react-")
    assert len(calls[0].id) > len("react-")


def test_react_text_handles_complex_arguments():
    """ReActTextProtocol should handle complex argument structures."""
    protocol = ReActTextProtocol()
    response = ModelResponse(
        content='```tool\n{"name": "test", "arguments": {"nested": {"key": "value"}, "list": [1, 2, 3]}}\n```',
        tool_calls=[],
    )
    content, calls = protocol.parse_response(response)
    assert len(calls) == 1
    assert calls[0].arguments == {"nested": {"key": "value"}, "list": [1, 2, 3]}


def test_react_text_handles_unicode_in_arguments():
    """ReActTextProtocol should handle unicode in arguments."""
    protocol = ReActTextProtocol()
    response = ModelResponse(
        content='```tool\n{"name": "test", "arguments": {"text": "café 世界 🎉"}}\n```',
        tool_calls=[],
    )
    content, calls = protocol.parse_response(response)
    assert len(calls) == 1
    assert calls[0].arguments == {"text": "café 世界 🎉"}


def test_react_text_multiline_tool_block():
    """ReActTextProtocol should handle multiline tool blocks."""
    protocol = ReActTextProtocol()
    response = ModelResponse(
        content='```tool\n{\n  "name": "test",\n  "arguments": {\n    "arg": "value"\n  }\n}\n```',
        tool_calls=[],
    )
    content, calls = protocol.parse_response(response)
    assert len(calls) == 1
    assert calls[0].name == "test"


def test_protocol_interface_compliance():
    """Both protocols should have required methods."""
    native = NativeToolsProtocol()
    react = ReActTextProtocol()

    # Check required methods exist
    assert hasattr(native, "render_system")
    assert hasattr(native, "prepare_request")
    assert hasattr(native, "parse_response")
    assert hasattr(react, "render_system")
    assert hasattr(react, "prepare_request")
    assert hasattr(react, "parse_response")

    # Check they are callable
    assert callable(native.render_system)
    assert callable(native.prepare_request)
    assert callable(native.parse_response)
    assert callable(react.render_system)
    assert callable(react.prepare_request)
    assert callable(react.parse_response)


def test_protocol_statelessness():
    """Protocols should be stateless (no side effects from calls)."""
    protocol = ReActTextProtocol()
    tools = [ToolSpec(name="test", description="Test", parameters={})]

    # Multiple calls should return consistent results
    result1 = protocol.render_system("base", tools)
    result2 = protocol.render_system("base", tools)
    assert result1 == result2


def test_react_text_with_special_characters_in_tool_name():
    """ReActTextProtocol should handle special characters in tool names."""
    protocol = ReActTextProtocol()
    response = ModelResponse(
        content='```tool\n{"name": "my_tool-name", "arguments": {}}\n```',
        tool_calls=[],
    )
    content, calls = protocol.parse_response(response)
    assert len(calls) == 1
    assert calls[0].name == "my_tool-name"
