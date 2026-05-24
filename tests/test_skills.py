"""Tests for skills functionality."""

from __future__ import annotations

from sele.config import LoopConfig, SkillsConfig
from sele.loops.base import LoopContext
from sele.registry import REGISTRY
from sele.skills import BaseSkill, ContextManagerSkill, ReflexionSkill
from sele.types import Message, ModelResponse, ToolResult


def test_skills_config_defaults():
    """Test that SkillsConfig has sensible defaults."""
    cfg = SkillsConfig()
    assert cfg.enabled is False
    assert cfg.skills == []
    assert cfg.breadth == 1
    assert cfg.depth == 1
    assert cfg.context_compression is False


def test_skills_config_with_values():
    """Test SkillsConfig with custom values."""
    cfg = SkillsConfig(
        enabled=True,
        skills=["reflexion", "context_manager"],
        breadth=3,
        depth=2,
        context_window=4096,
    )
    assert cfg.enabled is True
    assert cfg.skills == ["reflexion", "context_manager"]
    assert cfg.breadth == 3
    assert cfg.depth == 2
    assert cfg.context_window == 4096


def test_loop_config_includes_skills():
    """Test that LoopConfig includes skills configuration."""
    cfg = LoopConfig(kind="tool_loop", max_steps=10)
    assert hasattr(cfg, "skills")
    assert isinstance(cfg.skills, SkillsConfig)


def test_reflexion_skill_initialization():
    """Test ReflexionSkill initialization."""
    skill = ReflexionSkill()
    assert skill.name == "reflexion"
    assert skill.reflection_threshold == 3
    assert skill.max_reflections == 2
    assert skill.reflection_count == 0


def test_reflexion_skill_with_config():
    """Test ReflexionSkill with custom configuration."""
    skill = ReflexionSkill()
    
    # Mock LoopContext with skills config
    class MockContext:
        skills_config = {
            "skill_settings": {
                "reflexion": {
                    "reflection_threshold": 5,
                    "max_reflections": 3,
                }
            }
        }
    
    skill.initialize(MockContext())  # type: ignore
    assert skill.reflection_threshold == 5
    assert skill.max_reflections == 3


def test_context_manager_skill_initialization():
    """Test ContextManagerSkill initialization."""
    skill = ContextManagerSkill()
    assert skill.name == "context_manager"
    assert skill.max_context_chars == 8000
    assert skill.compression_ratio == 0.5


def test_context_manager_skill_with_config():
    """Test ContextManagerSkill with custom configuration."""
    skill = ContextManagerSkill()
    
    # Mock LoopContext with skills config
    class MockContext:
        skills_config = {
            "context_window": 4096,
            "skill_settings": {
                "context_manager": {
                    "max_context_chars": 4096,
                    "compression_ratio": 0.3,
                }
            }
        }
    
    skill.initialize(MockContext())  # type: ignore
    assert skill.max_context_chars == 4096
    assert skill.compression_ratio == 0.3


def test_base_skill_hooks():
    """Test that BaseSkill hooks can be overridden."""
    
    class TestSkill(BaseSkill):
        name = "test_skill"
        
        def __init__(self):
            self.init_called = False
            self.before_called = False
            self.after_called = False
            self.end_called = False
        
        def initialize(self, ctx):
            self.init_called = True
        
        def before_step(self, step_index, memory):
            self.before_called = True
        
        def after_step(self, step_index, response, tool_results):
            self.after_called = True
        
        def on_loop_end(self, final_text, total_steps):
            self.end_called = True
            return final_text + " [modified]"
    
    skill = TestSkill()
    
    # Test initialize
    skill.initialize(None)  # type: ignore
    assert skill.init_called is True
    
    # Test before_step
    skill.before_step(0, [])
    assert skill.before_called is True
    
    # Test after_step
    response = ModelResponse(content="test")
    skill.after_step(0, response, [])
    assert skill.after_called is True
    
    # Test on_loop_end
    result = skill.on_loop_end("test", 1)
    assert skill.end_called is True
    assert result == "test [modified]"


def test_skills_registered_in_registry():
    """Test that built-in skills are registered."""
    skills = REGISTRY.list("skills")
    assert "reflexion" in skills
    assert "context_manager" in skills


def test_skill_retrieval_from_registry():
    """Test retrieving skills from registry."""
    reflexion = REGISTRY.get("skills", "reflexion")
    assert reflexion is not None
    assert isinstance(reflexion, ReflexionSkill)
    
    context_mgr = REGISTRY.get("skills", "context_manager")
    assert context_mgr is not None
    assert isinstance(context_mgr, ContextManagerSkill)


def test_skill_on_loop_end_default():
    """Test that BaseSkill.on_loop_end returns text unchanged by default."""
    skill = BaseSkill()
    result = skill.on_loop_end("test output", 5)
    assert result == "test output"


def test_reflexion_skill_progress_tracking():
    """Test that ReflexionSkill tracks progress."""
    skill = ReflexionSkill()
    
    # Simulate steps with increasing response length
    response1 = ModelResponse(content="short")
    skill.after_step(0, response1, [])
    assert skill.steps_since_progress == 0
    
    # Same length response
    response2 = ModelResponse(content="short")
    skill.after_step(1, response2, [])
    assert skill.steps_since_progress == 1
    
    # Longer response
    response3 = ModelResponse(content="much longer response")
    skill.after_step(2, response3, [])
    assert skill.steps_since_progress == 0


def test_context_manager_skill_compression_trigger():
    """Test that ContextManagerSkill detects when compression is needed."""
    skill = ContextManagerSkill()
    skill.max_context_chars = 100
    
    # Create memory with content exceeding threshold
    memory = [
        Message(role="user", content="x" * 60),
        Message(role="assistant", content="y" * 60),
    ]
    
    skill.before_step(0, memory)
    assert skill.compression_triggered is True


def test_skills_config_with_skill_settings():
    """Test SkillsConfig with per-skill settings."""
    cfg = SkillsConfig(
        enabled=True,
        skills=["reflexion"],
        skill_settings={
            "reflexion": {
                "reflection_threshold": 5,
                "max_reflections": 3,
            }
        },
    )
    assert cfg.skill_settings["reflexion"]["reflection_threshold"] == 5
    assert cfg.skill_settings["reflexion"]["max_reflections"] == 3
