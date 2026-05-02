"""Tests for combat script data model and YAML loading."""
from __future__ import annotations

from pathlib import Path
from textwrap import dedent
from unittest.mock import patch

import pytest
import yaml

from anime_game_afk.games.aether_gazer.combat.script import (
    CombatScript,
    CombatStep,
    _CONFIG_DIR,
    delete_script_file,
    list_scripts,
    load_script,
    load_script_file,
    load_script_from_string,
    save_script_file,
    validate_script_id,
)


@pytest.fixture
def tmp_yaml(tmp_path: Path):
    """Helper: write YAML content to a temp file and return the path."""
    def _write(content: str) -> Path:
        p = tmp_path / "test_script.yaml"
        p.write_text(dedent(content), encoding="utf-8")
        return p
    return _write


class TestCombatStep:
    def test_press_step(self):
        step = CombatStep(action="press", key="j", vk_code=0x4A, duration=0.0, interval=0.12)
        assert step.action == "press"
        assert step.vk_code == 0x4A
        assert step.interval == 0.12

    def test_hold_step(self):
        step = CombatStep(action="hold", key="u", vk_code=0x55, duration=1.5, interval=0.12)
        assert step.action == "hold"
        assert step.duration == 1.5

    def test_wait_step(self):
        step = CombatStep(action="wait", key=None, vk_code=None, duration=0.5, interval=0.0)
        assert step.action == "wait"
        assert step.duration == 0.5


class TestLoadScriptFile:
    def test_basic_press_script(self, tmp_yaml):
        path = tmp_yaml("""\
            name: test
            interval: 0.1
            steps:
              - press: j
              - press: u
        """)
        script = load_script_file(path)
        assert script.name == "test"
        assert len(script.steps) == 2
        assert script.steps[0].action == "press"
        assert script.steps[0].vk_code == 0x4A  # J
        assert script.steps[0].interval == 0.1
        assert script.steps[1].vk_code == 0x55  # U

    def test_hold_step(self, tmp_yaml):
        path = tmp_yaml("""\
            name: hold_test
            interval: 0.12
            steps:
              - hold: u
                duration: 1.5
              - press: j
        """)
        script = load_script_file(path)
        assert script.steps[0].action == "hold"
        assert script.steps[0].vk_code == 0x55
        assert script.steps[0].duration == 1.5
        assert script.steps[1].action == "press"

    def test_wait_step(self, tmp_yaml):
        path = tmp_yaml("""\
            name: wait_test
            steps:
              - press: j
              - wait: 0.5
              - press: j
        """)
        script = load_script_file(path)
        assert len(script.steps) == 3
        assert script.steps[1].action == "wait"
        assert script.steps[1].duration == 0.5
        assert script.steps[1].key is None
        assert script.steps[1].vk_code is None

    def test_per_step_interval_override(self, tmp_yaml):
        path = tmp_yaml("""\
            name: override_test
            interval: 0.12
            steps:
              - press: j
                interval: 0.5
              - press: u
        """)
        script = load_script_file(path)
        assert script.steps[0].interval == 0.5
        assert script.steps[1].interval == 0.12

    def test_default_interval(self, tmp_yaml):
        path = tmp_yaml("""\
            name: default_interval
            steps:
              - press: j
        """)
        script = load_script_file(path)
        assert script.steps[0].interval == 0.12  # module default

    def test_description_optional(self, tmp_yaml):
        path = tmp_yaml("""\
            name: no_desc
            steps:
              - press: j
        """)
        script = load_script_file(path)
        assert script.description == ""

    def test_numeric_key_as_string(self, tmp_yaml):
        path = tmp_yaml("""\
            name: numeric
            steps:
              - press: "1"
              - press: "2"
        """)
        script = load_script_file(path)
        assert script.steps[0].vk_code == 0x31  # 1
        assert script.steps[1].vk_code == 0x32  # 2

    def test_space_key(self, tmp_yaml):
        path = tmp_yaml("""\
            name: space
            steps:
              - press: space
        """)
        script = load_script_file(path)
        assert script.steps[0].vk_code == 0x20

    def test_empty_steps_raises(self, tmp_yaml):
        path = tmp_yaml("""\
            name: empty
            steps: []
        """)
        with pytest.raises(ValueError, match="loop"):
            load_script_file(path)

    def test_missing_steps_raises(self, tmp_yaml):
        path = tmp_yaml("""\
            name: no_steps
        """)
        with pytest.raises(ValueError, match="loop"):
            load_script_file(path)

    def test_invalid_key_raises(self, tmp_yaml):
        path = tmp_yaml("""\
            name: bad_key
            steps:
              - press: "F12"
        """)
        with pytest.raises(ValueError):
            load_script_file(path)

    def test_hold_without_duration_raises(self, tmp_yaml):
        path = tmp_yaml("""\
            name: bad_hold
            steps:
              - hold: u
        """)
        with pytest.raises(ValueError, match="duration"):
            load_script_file(path)

    def test_ambiguous_step_raises(self, tmp_yaml):
        path = tmp_yaml("""\
            name: ambiguous
            steps:
              - press: j
                hold: u
        """)
        with pytest.raises(ValueError, match="exactly one"):
            load_script_file(path)


class TestLoadScript:
    def test_load_default(self):
        """Load the real default.yaml from config/combat_scripts/."""
        script = load_script("default")
        assert script.name == "默认连招"
        assert len(script.steps) == 10
        # First step is J (attack)
        assert script.steps[0].vk_code == 0x4A

    def test_load_shikoudi(self):
        """Load the real shikoudi.yaml from config/combat_scripts/."""
        script = load_script("shikoudi")
        assert script.name == "诗寇蒂"
        assert len(script.steps) == 7
        # First step is I (skill 2)
        assert script.steps[0].vk_code == 0x49

    def test_load_nonexistent_raises(self):
        with pytest.raises(FileNotFoundError):
            load_script("nonexistent_script_xyz")


class TestStartupLoopFormat:
    """Tests for the two-phase startup + loop script format."""

    def test_new_format_startup_and_loop(self, tmp_yaml):
        path = tmp_yaml("""\
            name: new_fmt
            startup:
              - press: u
            loop:
              - press: j
        """)
        script = load_script_file(path)
        assert script.name == "new_fmt"
        assert len(script.startup_steps) == 1
        assert script.startup_steps[0].vk_code == 0x55  # U
        assert len(script.loop_steps) == 1
        assert script.loop_steps[0].vk_code == 0x4A  # J

    def test_new_format_loop_only(self, tmp_yaml):
        path = tmp_yaml("""\
            name: loop_only
            loop:
              - press: j
        """)
        script = load_script_file(path)
        assert script.startup_steps == ()
        assert len(script.loop_steps) == 1

    def test_legacy_steps_treated_as_loop(self, tmp_yaml):
        path = tmp_yaml("""\
            name: legacy
            steps:
              - press: j
              - press: u
        """)
        script = load_script_file(path)
        assert script.startup_steps == ()
        assert len(script.loop_steps) == 2
        assert script.loop_steps[0].vk_code == 0x4A
        assert script.loop_steps[1].vk_code == 0x55

    def test_mixing_steps_and_loop_raises(self, tmp_yaml):
        path = tmp_yaml("""\
            name: bad_mix
            steps:
              - press: j
            loop:
              - press: u
        """)
        with pytest.raises(ValueError, match="not both"):
            load_script_file(path)

    def test_mixing_steps_and_startup_raises(self, tmp_yaml):
        path = tmp_yaml("""\
            name: bad_mix2
            steps:
              - press: j
            startup:
              - press: u
        """)
        with pytest.raises(ValueError, match="not both"):
            load_script_file(path)

    def test_empty_startup_ok(self, tmp_yaml):
        path = tmp_yaml("""\
            name: empty_startup
            startup: []
            loop:
              - press: j
        """)
        script = load_script_file(path)
        assert script.startup_steps == ()
        assert len(script.loop_steps) == 1

    def test_empty_loop_raises(self, tmp_yaml):
        path = tmp_yaml("""\
            name: empty_loop
            loop: []
        """)
        with pytest.raises(ValueError, match="loop"):
            load_script_file(path)

    def test_steps_property_concatenates(self):
        s1 = CombatStep(action="press", key="u", vk_code=0x55, duration=0.0, interval=0.12)
        s2 = CombatStep(action="press", key="j", vk_code=0x4A, duration=0.0, interval=0.12)
        script = CombatScript(name="cat", description="", startup_steps=(s1,), loop_steps=(s2,))
        assert script.steps == (s1, s2)
        assert len(script.steps) == 2

    def test_to_dict_roundtrip(self, tmp_yaml):
        path = tmp_yaml("""\
            name: roundtrip
            startup:
              - hold: space
                duration: 0.3
            loop:
              - press: j
              - press: u
        """)
        original = load_script_file(path)
        reloaded = load_script_from_string(original.to_yaml())
        assert reloaded.name == original.name
        assert reloaded.startup_steps == original.startup_steps
        assert reloaded.loop_steps == original.loop_steps

    def test_to_yaml_output(self, tmp_yaml):
        path = tmp_yaml("""\
            name: yaml_out
            loop:
              - press: j
        """)
        script = load_script_file(path)
        yaml_str = script.to_yaml()
        parsed = yaml.safe_load(yaml_str)
        assert isinstance(parsed, dict)
        assert parsed["name"] == "yaml_out"
        assert "loop" in parsed

    def test_unknown_top_level_key_raises(self, tmp_yaml):
        path = tmp_yaml("""\
            name: unknown
            foo: bar
            loop:
              - press: j
        """)
        with pytest.raises(ValueError, match="Unknown top-level"):
            load_script_file(path)

    def test_validate_script_id(self):
        assert validate_script_id("my_script") == "my_script"
        assert validate_script_id("test-123") == "test-123"
        assert validate_script_id("梵天") == "梵天"
        with pytest.raises(ValueError):
            validate_script_id("")
        with pytest.raises(ValueError):
            validate_script_id("a" * 100)
        with pytest.raises(ValueError):
            validate_script_id("bad/path")
        with pytest.raises(ValueError):
            validate_script_id("bad.ext")

    def test_load_fantian_new_format(self):
        script = load_script("fantian")
        assert script.name == "梵天"
        assert len(script.startup_steps) == 1
        assert script.startup_steps[0].action == "hold"
        assert script.startup_steps[0].vk_code == 0x20  # space
        assert len(script.loop_steps) > 0
        assert script.loop_steps[0].action == "press"


class TestScriptCRUD:
    """Tests for save / delete / list operations."""

    def test_save_and_load(self, tmp_path):
        content = dedent("""\
            name: saved
            loop:
              - press: j
        """)
        with patch("anime_game_afk.games.aether_gazer.combat.script._CONFIG_DIR", tmp_path):
            path = save_script_file("saved", content)
            assert path.exists()
            script = load_script_file(path)
            assert script.name == "saved"
            assert len(script.loop_steps) == 1

    def test_save_invalid_content_raises(self, tmp_path):
        with patch("anime_game_afk.games.aether_gazer.combat.script._CONFIG_DIR", tmp_path):
            with pytest.raises((ValueError, yaml.YAMLError)):
                save_script_file("bad", "not: valid: yaml: combat: script")

    def test_delete_default_raises(self, tmp_path):
        with patch("anime_game_afk.games.aether_gazer.combat.script._CONFIG_DIR", tmp_path):
            with pytest.raises(ValueError, match="default"):
                delete_script_file("default")

    def test_delete_nonexistent_ok(self, tmp_path):
        with patch("anime_game_afk.games.aether_gazer.combat.script._CONFIG_DIR", tmp_path):
            delete_script_file("nonexistent")  # should not raise

    def test_list_scripts(self, tmp_path):
        content = dedent("""\
            name: listed
            loop:
              - press: j
        """)
        (tmp_path / "listed.yaml").write_text(content, encoding="utf-8")
        with patch("anime_game_afk.games.aether_gazer.combat.script._CONFIG_DIR", tmp_path):
            scripts = list_scripts()
            assert len(scripts) == 1
            assert scripts[0]["id"] == "listed"
            assert scripts[0]["name"] == "listed"
            assert scripts[0]["has_startup"] is False
            assert scripts[0]["loop_count"] == 1
