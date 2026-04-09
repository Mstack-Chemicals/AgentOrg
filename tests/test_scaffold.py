"""Tests for agentorg.scaffold."""

import json
import os
import re
import time

import pytest

from agentorg.scaffold import create_run_directory


@pytest.fixture
def work_dir(tmp_path, monkeypatch):
    """Change into a fresh temp directory for each test."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


class TestCreateRunDirectory:
    def test_run_directory_created(self, work_dir):
        result = create_run_directory()
        assert os.path.isdir(result["run_dir"])
        # Timestamp matches YYYYMMDDTHHMMSS
        assert re.match(r"^\d{8}T\d{6}$", result["timestamp"])

    def test_symlink_updated(self, work_dir):
        result = create_run_directory()
        symlink = os.path.join(".agentorg", "runs", "latest")
        assert os.path.islink(symlink)
        target = os.readlink(symlink)
        assert target == result["timestamp"]

    def test_run_subdirectories_created(self, work_dir):
        result = create_run_directory()
        run_dir = result["run_dir"]
        for subdir in ("handoffs", "reviews", "blocked", "logs"):
            assert os.path.isdir(os.path.join(run_dir, subdir))

    def test_budget_ledger_initial(self, work_dir):
        result = create_run_directory()
        ledger_path = os.path.join(result["run_dir"], "budget-ledger.json")
        assert os.path.exists(ledger_path)
        with open(ledger_path) as f:
            ledger = json.load(f)
        assert ledger["cap"] is None
        assert ledger["total_consumed"] == 0
        assert ledger["consumed"]["research"] == 0
        assert ledger["consumed"]["cto"] == 0

    def test_run_log_created(self, work_dir):
        result = create_run_directory()
        assert os.path.exists(
            os.path.join(result["run_dir"], "logs", "run-log.md")
        )

    def test_cross_run_logs_created(self, work_dir):
        create_run_directory()
        logs_dir = os.path.join(".agentorg", "logs")
        for name in (
            "estimation-accuracy.log",
            "complexity-delta.log",
            "task-deviations.log",
        ):
            assert os.path.exists(os.path.join(logs_dir, name))

    def test_decisions_md_created(self, work_dir):
        create_run_directory()
        assert os.path.exists(os.path.join(".agentorg", "decisions.md"))

    def test_memory_directories_created(self, work_dir):
        create_run_directory()
        for agent in (
            "cto",
            "research-lead",
            "architect",
            "engineering-lead",
            "devops-lead",
        ):
            assert os.path.isdir(
                os.path.join(".agentorg", "memory", agent)
            )

    def test_existing_decisions_not_overwritten(self, work_dir):
        os.makedirs(".agentorg", exist_ok=True)
        decisions_path = os.path.join(".agentorg", "decisions.md")
        with open(decisions_path, "w") as f:
            f.write("prior decision content")

        create_run_directory()

        with open(decisions_path) as f:
            assert f.read() == "prior decision content"

    def test_existing_memory_not_overwritten(self, work_dir):
        mem_dir = os.path.join(".agentorg", "memory", "cto")
        os.makedirs(mem_dir, exist_ok=True)
        mem_file = os.path.join(mem_dir, "note.md")
        with open(mem_file, "w") as f:
            f.write("important note")

        create_run_directory()

        with open(mem_file) as f:
            assert f.read() == "important note"

    def test_multiple_runs_create_separate_dirs(self, work_dir):
        r1 = create_run_directory()
        time.sleep(1.1)  # ensure different timestamp
        r2 = create_run_directory()
        assert r1["timestamp"] != r2["timestamp"]
        assert os.path.isdir(r1["run_dir"])
        assert os.path.isdir(r2["run_dir"])
        # Symlink points to latest
        target = os.readlink(os.path.join(".agentorg", "runs", "latest"))
        assert target == r2["timestamp"]

    def test_claude_agents_dir_created(self, work_dir):
        create_run_directory()
        assert os.path.isdir(os.path.join(".claude", "agents"))

    def test_src_dir_created_greenfield(self, work_dir):
        create_run_directory(is_greenfield=True)
        assert os.path.isdir("src")

    def test_src_dir_not_created_existing(self, work_dir):
        create_run_directory(is_greenfield=False)
        assert not os.path.isdir("src")

    def test_phase_status_created(self, work_dir):
        result = create_run_directory()
        assert os.path.exists(
            os.path.join(result["run_dir"], "phase-status.md")
        )

    def test_init_context_placeholder_created(self, work_dir):
        result = create_run_directory()
        assert os.path.exists(
            os.path.join(result["run_dir"], "init-context.md")
        )
