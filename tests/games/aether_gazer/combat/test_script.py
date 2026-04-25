"""Tests for combat script data model and YAML loading."""
from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest
import yaml

from anime_game_afk.games.aether_gazer.combat.script import (
    CombatScript,
    CombatStep,
    load_script,
    load_script_file,
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
        with pytest.raises(ValueError, match="steps"):
            load_script_file(path)

    def test_missing_steps_raises(self, tmp_yaml):
        path = tmp_yaml("""\
            name: no_steps
        """)
        with pytest.raises(ValueError, match="steps"):
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
