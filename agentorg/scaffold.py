"""Create the .agentorg/ directory structure for a run."""

from __future__ import annotations

import datetime
import json
import os
import subprocess


def _touch_if_absent(path: str, content: str = "") -> None:
    """Create a file with content only if it does not already exist."""
    if not os.path.exists(path):
        with open(path, "w") as f:
            f.write(content)


def _initial_budget_ledger(timestamp: str) -> str:
    """Return the initial budget-ledger.json content."""
    ledger = {
        "cap": None,
        "estimated_total": None,
        "phase_allocations": {
            "research": None,
            "architect": None,
            "engineering": None,
            "devops": None,
        },
        "consumed": {
            "research": 0,
            "architect": 0,
            "engineering": 0,
            "devops": 0,
            "cto": 0,
        },
        "total_consumed": 0,
        "remaining": None,
        "last_updated": datetime.datetime.now().isoformat(),
    }
    return json.dumps(ledger, indent=2)


def create_run_directory(is_greenfield: bool = True) -> dict:
    """Create the full .agentorg/ directory structure.

    Args:
        is_greenfield: If True, create src/ directory. If False, skip it
            (existing codebase has its own structure).

    Returns:
        {"run_dir": str, "timestamp": str, "git_status": str}
        git_status is "initialised" or "created new repo".
    """
    timestamp = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
    run_dir = os.path.join(".agentorg", "runs", timestamp)

    # --- Run-specific directories ---
    for subdir in (
        run_dir,
        os.path.join(run_dir, "handoffs"),
        os.path.join(run_dir, "reviews"),
        os.path.join(run_dir, "blocked"),
        os.path.join(run_dir, "logs"),
    ):
        os.makedirs(subdir, exist_ok=True)

    # --- Run-specific placeholder files ---
    _touch_if_absent(os.path.join(run_dir, "init-context.md"))
    _touch_if_absent(os.path.join(run_dir, "phase-status.md"))
    _touch_if_absent(
        os.path.join(run_dir, "budget-ledger.json"),
        _initial_budget_ledger(timestamp),
    )
    _touch_if_absent(os.path.join(run_dir, "logs", "run-log.md"))

    # --- Cross-run directories ---
    os.makedirs(os.path.join(".agentorg", "logs"), exist_ok=True)

    # --- Cross-run log files (never overwrite) ---
    for log_name in (
        "estimation-accuracy.log",
        "complexity-delta.log",
        "task-deviations.log",
    ):
        _touch_if_absent(os.path.join(".agentorg", "logs", log_name))

    # --- decisions.md (never overwrite) ---
    _touch_if_absent(
        os.path.join(".agentorg", "decisions.md"),
        "# decisions.md — append-only, persists across runs\n",
    )

    # --- Memory directories (never overwrite contents) ---
    for agent_name in (
        "cto",
        "research-lead",
        "architect",
        "engineering-lead",
        "devops-lead",
    ):
        os.makedirs(
            os.path.join(".agentorg", "memory", agent_name), exist_ok=True
        )

    # --- Update latest symlink ---
    symlink_path = os.path.join(".agentorg", "runs", "latest")
    if os.path.islink(symlink_path):
        os.unlink(symlink_path)
    elif os.path.exists(symlink_path):
        os.remove(symlink_path)
    os.symlink(timestamp, symlink_path)

    # --- .claude/agents/ directory ---
    os.makedirs(os.path.join(".claude", "agents"), exist_ok=True)

    # --- src/ directory (greenfield only) ---
    if is_greenfield:
        os.makedirs("src", exist_ok=True)

    # --- Git init if needed ---
    if os.path.isdir(".git"):
        git_status = "initialised"
    else:
        try:
            subprocess.run(
                ["git", "init"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            git_status = "created new repo"
        except (FileNotFoundError, subprocess.TimeoutExpired):
            git_status = "git not available"

    return {
        "run_dir": run_dir,
        "timestamp": timestamp,
        "git_status": git_status,
    }
