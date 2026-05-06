"""Tests for agentorg.init_flow (via CLI)."""

import os
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from agentorg.cli import main


VALID_OBJECTIVE = """\
## Goal
Build a REST API that serves weather data from a PostgreSQL database.

## Constraints
- Python 3.11 only
- Must use existing PostgreSQL database

## Out of Scope
- No frontend or UI of any kind
- No production deployment

## Success Criteria

### Research Phase
- PRDs produced for API design and data model

### Engineering Phase
- All endpoints pass integration tests

### DevOps Phase
- CI pipeline runs on every push
"""


@pytest.fixture
def runner():
    return CliRunner()


class TestInit:
    def test_init_creates_files(self, runner, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(main, ["init"])
        assert result.exit_code == 0
        assert os.path.exists("objective.template.md")
        assert os.path.exists("CLAUDE.md")
        assert os.path.exists(os.path.join(".claude", "settings.json"))

    def test_init_does_not_overwrite(self, runner, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        with open("objective.template.md", "w") as f:
            f.write("my custom template")

        result = runner.invoke(main, ["init"])
        assert result.exit_code == 0

        with open("objective.template.md") as f:
            assert f.read() == "my custom template"

    def test_init_output_created(self, runner, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(main, ["init"])
        assert "\u2713 Created objective.template.md" in result.output
        assert "\u2713 Created CLAUDE.md" in result.output
        assert "Next step:" in result.output

    def test_init_shows_ready_when_objective_exists(self, runner, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        with open("objective.md", "w") as f:
            f.write("## Goal\nBuild something.\n")
        result = runner.invoke(main, ["init"])
        assert "objective.md found" in result.output
        assert "Ready" in result.output

    def test_init_output_existing(self, runner, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        # Create all three files first
        runner.invoke(main, ["init"])
        # Run init again
        result = runner.invoke(main, ["init"])
        assert "nothing overwritten" in result.output
        assert "~ objective.template.md exists" in result.output


class TestRun:
    def test_run_halts_on_missing_objective(self, runner, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(main, ["run"])
        assert result.exit_code != 0
        assert "not found" in result.output

    def test_run_halts_on_missing_goal(self, runner, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        with open("objective.md", "w") as f:
            f.write("## Constraints\n- Python 3.11\n\n## Out of Scope\n- No frontend\n")
        result = runner.invoke(main, ["run"])
        assert result.exit_code != 0
        assert "Goal is missing" in result.output

    def test_run_halts_on_missing_constraints(self, runner, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        with open("objective.md", "w") as f:
            f.write("## Goal\nBuild an API.\n\n## Out of Scope\n- No frontend\n")
        result = runner.invoke(main, ["run"])
        assert result.exit_code != 0
        assert "Constraints" in result.output

    @patch("agentorg.init_flow.subprocess.run")
    def test_run_validates_successfully(
        self, mock_subproc, runner, tmp_path, monkeypatch
    ):
        """Valid objective.md with criteria → validation passes, blocks at confirmation."""
        monkeypatch.chdir(tmp_path)
        mock_subproc.return_value = MagicMock(returncode=0, stdout="")

        with open("objective.md", "w") as f:
            f.write(VALID_OBJECTIVE)

        # Create CLAUDE.md from template so _populate_claude_md works
        from agentorg.init_flow import _get_template
        with open("CLAUDE.md", "w") as f:
            f.write(_get_template("CLAUDE.md"))

        # Provide enter keypress for success criteria confirmation
        result = runner.invoke(main, ["run"], input="\n")

        assert result.exit_code == 0
        assert "\u2713 Goal" in result.output
        assert "\u2713 Constraints" in result.output
        assert "\u2713 Out of scope" in result.output
        assert "INIT COMPLETE" in result.output

    @patch("agentorg.init_flow.subprocess.run")
    def test_run_full_flow(
        self, mock_subproc, runner, tmp_path, monkeypatch
    ):
        """Full run with valid objective: scaffolds dirs, copies agents, writes init-context."""
        monkeypatch.chdir(tmp_path)
        mock_subproc.return_value = MagicMock(returncode=0, stdout="")

        with open("objective.md", "w") as f:
            f.write(VALID_OBJECTIVE)

        from agentorg.init_flow import _get_template
        with open("CLAUDE.md", "w") as f:
            f.write(_get_template("CLAUDE.md"))

        result = runner.invoke(main, ["run"], input="\n")
        assert result.exit_code == 0
        assert "INIT COMPLETE" in result.output

        # Verify scaffolding
        assert os.path.isdir(".agentorg")
        assert os.path.isdir(os.path.join(".agentorg", "runs"))
        assert os.path.islink(os.path.join(".agentorg", "runs", "latest"))

        # Verify agents copied
        agents_dir = os.path.join(".claude", "agents")
        assert os.path.isdir(agents_dir)
        assert os.path.exists(os.path.join(agents_dir, "cto.md"))
        assert os.path.exists(os.path.join(agents_dir, "sde1.md"))

        # Verify init-context.md written
        latest = os.readlink(os.path.join(".agentorg", "runs", "latest"))
        run_dir = os.path.join(".agentorg", "runs", latest)
        init_context = os.path.join(run_dir, "init-context.md")
        assert os.path.exists(init_context)
        with open(init_context) as f:
            content = f.read()
        assert "weather data" in content

    @patch("agentorg.init_flow.subprocess.run")
    def test_run_populates_claude_md(
        self, mock_subproc, runner, tmp_path, monkeypatch
    ):
        """CLAUDE.md [FIXED] sections get populated with constraints and out-of-scope."""
        monkeypatch.chdir(tmp_path)
        mock_subproc.return_value = MagicMock(returncode=0, stdout="")

        with open("objective.md", "w") as f:
            f.write(VALID_OBJECTIVE)

        from agentorg.init_flow import _get_template
        with open("CLAUDE.md", "w") as f:
            f.write(_get_template("CLAUDE.md"))

        result = runner.invoke(main, ["run"], input="\n")
        assert result.exit_code == 0

        with open("CLAUDE.md") as f:
            claude_content = f.read()
        assert "Python 3.11 only" in claude_content
        assert "No frontend or UI of any kind" in claude_content
        assert "PLACEHOLDER" not in claude_content


class TestVersion:
    def test_version_output(self, runner):
        result = runner.invoke(main, ["version"])
        assert result.exit_code == 0
        assert "agentorg v" in result.output
