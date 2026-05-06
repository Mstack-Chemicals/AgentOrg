"""Init flow — orchestrates agentorg init and agentorg run."""

from __future__ import annotations

import datetime
import json
import os
import shutil
import subprocess
from pathlib import Path

import click

from agentorg.environment import (
    check_prerequisites,
    filter_relevant_runtimes,
    scan_environment,
)
from agentorg.scaffold import create_run_directory
from agentorg.validator import parse_objective, validate_objective
from agentorg.version import __version__

_PACKAGE_DIR = Path(__file__).parent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_template(name: str) -> str:
    """Read a bundled template file."""
    return (_PACKAGE_DIR / "templates" / name).read_text()


def _write_if_absent(path: str, content: str) -> bool:
    """Write *content* to *path* only if the file does not exist.

    Returns True if the file was created, False if it already existed.
    """
    if os.path.exists(path):
        return False
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        f.write(content)
    return True


def _wait_for_enter() -> None:
    """Block until the user presses enter."""
    try:
        input()
    except (EOFError, KeyboardInterrupt):
        raise SystemExit(1)


# ---------------------------------------------------------------------------
# Environment isolation — conda env or venv
# ---------------------------------------------------------------------------


def _detect_python_version(constraints: list[str]) -> str:
    """Extract a Python version from constraints, or return default."""
    import re

    for c in constraints:
        # Match patterns like "Python 3.11", "Python 3.10+", "python >= 3.12"
        m = re.search(r"[Pp]ython\s*[>=]*\s*(3\.\d+)", c)
        if m:
            return m.group(1)
    return "3.10"


def _create_project_env(env_name: str, python_version: str) -> dict:
    """Create an isolated project environment.

    Tries conda first, falls back to python venv.

    Returns:
        {"type": "conda" | "venv", "name": str, "prefix": str}
        or {"type": "failed", "reason": str}
    """
    # --- Try conda ---
    if shutil.which("conda"):
        result = subprocess.run(
            [
                "conda", "create", "-n", env_name,
                f"python={python_version}", "-y", "--quiet",
            ],
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode == 0:
            # Get the env prefix path
            prefix_result = subprocess.run(
                ["conda", "info", "--envs"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            prefix = ""
            for line in prefix_result.stdout.splitlines():
                if env_name in line:
                    parts = line.split()
                    # The path is the last token on the line
                    prefix = parts[-1] if parts else ""
                    break
            return {"type": "conda", "name": env_name, "prefix": prefix}

    # --- Fallback: python venv ---
    venv_path = os.path.join(".venv")
    python_bin = shutil.which(f"python{python_version}") or shutil.which("python3")
    if python_bin:
        result = subprocess.run(
            [python_bin, "-m", "venv", venv_path],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0:
            return {
                "type": "venv",
                "name": env_name,
                "prefix": os.path.abspath(venv_path),
            }

    return {"type": "failed", "reason": "Neither conda nor python venv available"}


# ---------------------------------------------------------------------------
# Success criteria generation via Claude API
# ---------------------------------------------------------------------------


def _generate_success_criteria(
    objective_data: dict, env: dict
) -> dict[str, list[str]] | None:
    """Call Claude API (Haiku) to draft success criteria.

    Returns {"research": [...], "engineering": [...], "devops": [...]} or None
    on any failure.
    """
    try:
        import anthropic  # noqa: F811
    except ImportError:
        return None

    stack_str = ", ".join(env.get("detected_stack", [])) or "none detected"
    constraints_str = "\n".join(
        f"- {c}" for c in objective_data["constraints"]
    )
    oos_str = "\n".join(f"- {s}" for s in objective_data["out_of_scope"])

    prompt = (
        "Given this project objective, generate draft success criteria "
        "for each phase.\n\n"
        f"Goal: {objective_data['goal']}\n\n"
        f"Constraints:\n{constraints_str}\n\n"
        f"Out of Scope:\n{oos_str}\n\n"
        f"Detected Stack: {stack_str}\n\n"
        "Generate 2-4 verifiable success criteria for each phase:\n"
        "- Research Phase: criteria about what research should produce\n"
        "- Engineering Phase: criteria about what code should accomplish\n"
        "- DevOps Phase: criteria about deployment and CI\n\n"
        "Each criterion must be verifiable — testable or readable from output.\n"
        "Return ONLY the criteria in this exact format:\n\n"
        "### Research Phase\n- criterion 1\n- criterion 2\n\n"
        "### Engineering Phase\n- criterion 1\n- criterion 2\n\n"
        "### DevOps Phase\n- criterion 1\n- criterion 2"
    )

    try:
        client = anthropic.Anthropic()
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        return _parse_criteria_response(response.content[0].text)
    except Exception:
        return None


def _parse_criteria_response(text: str) -> dict[str, list[str]] | None:
    """Parse markdown criteria response into structured dict."""
    import re

    criteria: dict[str, list[str]] = {
        "research": [],
        "engineering": [],
        "devops": [],
    }

    parts = re.split(r"^### ", text, flags=re.MULTILINE)
    for part in parts[1:]:
        lines = part.split("\n", 1)
        heading = lines[0].strip().lower()
        body = lines[1] if len(lines) > 1 else ""

        items = []
        for line in body.split("\n"):
            match = re.match(r"^\s*-\s+(.+)", line)
            if match:
                items.append(match.group(1).strip())

        if "research" in heading:
            criteria["research"] = items
        elif "engineering" in heading:
            criteria["engineering"] = items
        elif "devops" in heading:
            criteria["devops"] = items

    if not any(criteria.values()):
        return None
    return criteria


def _append_success_criteria_to_objective(
    path: str, criteria: dict[str, list[str]]
) -> None:
    """Append or replace the Success Criteria section in objective.md."""
    with open(path, "r") as f:
        content = f.read()

    criteria_md = "\n## Success Criteria\n"
    for phase_name, key in [
        ("Research Phase", "research"),
        ("Engineering Phase", "engineering"),
        ("DevOps Phase", "devops"),
    ]:
        criteria_md += f"\n### {phase_name}\n"
        for item in criteria.get(key, []):
            criteria_md += f"- {item}\n"

    # If section already exists, replace it
    import re

    if re.search(r"^## Success Criteria", content, re.MULTILINE):
        # Remove everything from ## Success Criteria to the next ## or end
        content = re.sub(
            r"## Success Criteria.*?(?=\n## |\Z)",
            "",
            content,
            flags=re.DOTALL,
        )

    # Append before ## Budget Cap if it exists, otherwise at end
    budget_match = re.search(r"\n## Budget Cap", content)
    if budget_match:
        insert_pos = budget_match.start()
        content = content[:insert_pos] + criteria_md + content[insert_pos:]
    else:
        content = content.rstrip() + "\n" + criteria_md

    with open(path, "w") as f:
        f.write(content)


def _display_criteria(criteria: dict[str, list[str]]) -> None:
    """Print criteria to terminal in the spec's format."""
    for phase_name, key in [
        ("Research Phase", "research"),
        ("Engineering Phase", "engineering"),
        ("DevOps Phase", "devops"),
    ]:
        click.echo(f"\n  {phase_name}")
        for item in criteria.get(key, []):
            click.echo(f"  - {item}")


# ---------------------------------------------------------------------------
# init-context.md generation
# ---------------------------------------------------------------------------


def _write_init_context(
    run_dir: str, objective_data: dict, env: dict
) -> None:
    """Write init-context.md to the run directory."""
    budget_cap = objective_data.get("budget_cap")
    budget_str = str(budget_cap) if budget_cap is not None else "null"

    sc = objective_data.get("success_criteria") or {
        "research": [],
        "engineering": [],
        "devops": [],
    }

    def _fmt_list(items: list[str], indent: int = 2) -> str:
        prefix = " " * indent
        return "\n".join(f"{prefix}- {item}" for item in items)

    content = f"""# init-context.md

## Objective
goal: {objective_data['goal']}
constraints:
{_fmt_list(objective_data['constraints'])}
out_of_scope:
{_fmt_list(objective_data['out_of_scope'])}
success_criteria:
  research:
{_fmt_list(sc['research'], 4)}
  engineering:
{_fmt_list(sc['engineering'], 4)}
  devops:
{_fmt_list(sc['devops'], 4)}

## Environment
os: {env['os']}
shell: {env['shell']}
language_runtimes: {json.dumps(env['language_runtimes'])}
package_managers: {json.dumps(env['package_managers'])}
git_config:
  user: {env['git_config']['user']}
  default_branch: {env['git_config']['default_branch']}
available_tools: {json.dumps(env['available_tools'])}

## Project State
is_greenfield: {str(env['is_greenfield']).lower()}
existing_structure: {env['existing_structure']}
detected_stack: {json.dumps(env['detected_stack'])}

## Run Metadata
initiated_at: {datetime.datetime.now().isoformat()}
budget_cap: {budget_str}
"""

    with open(os.path.join(run_dir, "init-context.md"), "w") as f:
        f.write(content)


# ---------------------------------------------------------------------------
# CLAUDE.md [FIXED] section population
# ---------------------------------------------------------------------------


def _populate_claude_md(
    objective_data: dict,
    env_run_prefix: str = "",
    env: dict | None = None,
) -> None:
    """Fill in [FIXED] placeholder sections in CLAUDE.md with objective data."""
    with open("CLAUDE.md", "r") as f:
        content = f.read()

    # Replace application code root placeholder
    code_root = env.get("code_root", "src/") if env else "src/"
    content = content.replace(
        "APPLICATION_CODE_ROOT_PLACEHOLDER", code_root
    )

    lines = content.splitlines(keepends=True)

    output: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        output.append(line)

        # After [FIXED] Hard Constraints — replace PLACEHOLDER
        if line.startswith("## [FIXED] Hard Constraints"):
            i += 1
            while i < len(lines) and not lines[i].startswith("## "):
                if "PLACEHOLDER" in lines[i]:
                    for c in objective_data["constraints"]:
                        output.append(f"- {c}\n")
                    output.append("\n")
                else:
                    output.append(lines[i])
                i += 1
            continue

        # After [FIXED] Out of Scope — replace PLACEHOLDER
        if line.startswith("## [FIXED] Out of Scope"):
            i += 1
            while i < len(lines) and not lines[i].startswith("## "):
                if "PLACEHOLDER" in lines[i]:
                    for s in objective_data["out_of_scope"]:
                        output.append(f"- {s}\n")
                    output.append("\n")
                else:
                    output.append(lines[i])
                i += 1
            continue

        # After [FIXED] Environment Isolation — replace PLACEHOLDER
        if line.startswith("## [FIXED] Environment Isolation"):
            i += 1
            while i < len(lines) and not lines[i].startswith("## "):
                if "PLACEHOLDER" in lines[i]:
                    output.append(
                        "All shell commands that install packages, run code, "
                        "or execute tests\n"
                    )
                    output.append(
                        "MUST run inside the project environment using "
                        "the following prefix:\n"
                    )
                    output.append(f"\n    {env_run_prefix}\n\n")
                    output.append(
                        "Example: {prefix} pip install -r requirements.txt\n"
                        .format(prefix=env_run_prefix)
                    )
                    output.append(
                        "Example: {prefix} python -m pytest\n\n"
                        .format(prefix=env_run_prefix)
                    )
                    output.append(
                        "No agent may install packages to the system Python.\n"
                    )
                    output.append(
                        "No agent may modify any environment other than "
                        "the project environment.\n"
                    )
                    output.append(
                        "Environment details are in .agentorg/env.\n"
                    )
                    output.append("\n")
                else:
                    output.append(lines[i])
                i += 1
            continue

        # After [FIXED] Existing Codebase Rules — replace PLACEHOLDER
        if line.startswith("## [FIXED] Existing Codebase Rules"):
            i += 1
            while i < len(lines) and not lines[i].startswith("## "):
                if "PLACEHOLDER" in lines[i]:
                    is_greenfield = (
                        env.get("is_greenfield", True) if env else True
                    )
                    existing_structure = (
                        env.get("existing_structure", "none") if env else "none"
                    )
                    detected_stack = (
                        env.get("detected_stack", []) if env else []
                    )

                    output.append(
                        f"Project type: "
                        f"{'greenfield' if is_greenfield else 'existing codebase'}\n"
                    )
                    if not is_greenfield:
                        output.append(
                            f"Existing structure: {existing_structure}\n"
                        )
                        if detected_stack:
                            output.append(
                                f"Detected stack: {', '.join(detected_stack)}\n"
                            )
                        output.append("\n")
                        output.append(
                            "This project has an existing codebase. "
                            "The following rules are MANDATORY:\n\n"
                        )
                        output.append(
                            "1. READ BEFORE WRITE: Every agent must read and "
                            "understand the existing code\n"
                            "   structure, patterns, and conventions before "
                            "producing any output.\n"
                        )
                        output.append(
                            "2. PRESERVE EXISTING FUNCTIONALITY: No agent may "
                            "break existing functionality.\n"
                            "   All existing tests must continue to pass after "
                            "any modification.\n"
                        )
                        output.append(
                            "3. FOLLOW EXISTING PATTERNS: New code must follow "
                            "the conventions, naming\n"
                            "   patterns, directory structure, and architectural "
                            "style of the existing codebase.\n"
                            "   Do not introduce new patterns unless the existing "
                            "ones are demonstrably inadequate\n"
                            "   for the new feature.\n"
                        )
                        output.append(
                            "4. ADDITIVE CHANGES: Prefer adding new files and "
                            "functions over modifying\n"
                            "   existing ones. When modifying existing code is "
                            "necessary, make the smallest\n"
                            "   change possible.\n"
                        )
                        output.append(
                            "5. INTEGRATION TESTING: Every change that touches "
                            "existing code must include\n"
                            "   integration tests verifying that existing "
                            "functionality is unaffected.\n"
                        )
                        output.append(
                            "6. CODEBASE SURVEY: The CTO must include a codebase "
                            "summary in the research-brief\n"
                            "   so all downstream agents understand the existing "
                            "architecture.\n"
                        )
                    else:
                        output.append(
                            "\nThis is a greenfield project. No existing "
                            "codebase rules apply.\n"
                        )
                    output.append("\n")
                else:
                    output.append(lines[i])
                i += 1
            continue

        i += 1

    with open("CLAUDE.md", "w") as f:
        f.writelines(output)


# ---------------------------------------------------------------------------
# Copy agent files
# ---------------------------------------------------------------------------


def _copy_agents() -> None:
    """Copy all agent .md files from the package bundle to .claude/agents/."""
    agents_src = _PACKAGE_DIR / "agents"
    agents_dst = Path(".claude") / "agents"
    agents_dst.mkdir(parents=True, exist_ok=True)

    for agent_file in agents_src.glob("*.md"):
        shutil.copy2(agent_file, agents_dst / agent_file.name)


def _copy_schemas() -> None:
    """Copy schema .md files from the package bundle to .agentorg/schemas/."""
    schemas_src = _PACKAGE_DIR / "schemas"
    schemas_dst = Path(".agentorg") / "schemas"
    schemas_dst.mkdir(parents=True, exist_ok=True)

    for schema_file in schemas_src.glob("*.md"):
        if schema_file.name == "README.md":
            continue
        shutil.copy2(schema_file, schemas_dst / schema_file.name)


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------


def initialise() -> None:
    """agentorg init — create project files from templates."""
    click.echo(f"agentorg v{__version__}")
    click.echo()
    click.echo(f"Initialising project in {os.getcwd()}...")
    click.echo()

    files = {
        "objective.template.md": _get_template("objective.template.md"),
        "CLAUDE.md": _get_template("CLAUDE.md"),
        os.path.join(".claude", "settings.json"): _get_template(
            "settings.json"
        ),
    }

    created_any = False

    for filepath, content in files.items():
        if _write_if_absent(filepath, content):
            click.echo(f"  \u2713 Created {filepath}")
            created_any = True
        else:
            click.echo(f"  ~ {filepath} exists")

    if not created_any:
        click.echo()
        click.echo("Files already present \u2014 nothing overwritten.")

    click.echo()
    if os.path.exists("objective.md"):
        click.echo("  \u2713 objective.md found")
        click.echo()
        click.echo("Ready. Run: agentorg run")
    else:
        click.echo("Next step:")
        click.echo("  Create objective.md using the template as a schema reference.")
        click.echo("  See objective.template.md for the required format.")
        click.echo("  You can use any tool to generate it from an existing PRD.")
        click.echo()
        click.echo("  Once objective.md is ready, run: agentorg start")


def run() -> None:
    """agentorg run — validate, scaffold, and prepare CTO handoff."""
    click.echo(f"agentorg v{__version__}")

    # ------------------------------------------------------------------
    # Touchpoint 2 — Validation
    # ------------------------------------------------------------------
    click.echo()
    click.echo("Validating objective.md...")
    errors = validate_objective("objective.md")
    if errors:
        click.echo(f"  \u2717 {errors[0]}")
        raise SystemExit(1)

    objective_data = parse_objective("objective.md")

    click.echo("  \u2713 Goal")
    click.echo("  \u2713 Constraints")
    click.echo("  \u2713 Out of scope")
    budget_display = (
        str(objective_data["budget_cap"])
        if objective_data["budget_cap"]
        else "not set"
    )
    click.echo(f"  \u2713 Budget cap: {budget_display}")

    # ------------------------------------------------------------------
    # Touchpoint 3 — Environment scan
    # ------------------------------------------------------------------
    click.echo()
    click.echo("Scanning environment...")
    env = scan_environment()

    # Apply user-specified code_root early so git/stack checks use it
    user_code_root = objective_data.get("code_root")
    if user_code_root:
        env["code_root"] = user_code_root
        # Re-check git inside the user-specified code root
        code_root_dir = user_code_root.rstrip("/")
        if os.path.isdir(os.path.join(code_root_dir, ".git")):
            env["has_git"] = True
        # Re-detect stack with the user-specified code root
        from agentorg.environment import _detect_stack

        env["detected_stack"] = _detect_stack([code_root_dir])

    # Git init if needed (before displaying git status)
    if env.get("has_git", False):
        git_display = "initialised"
    else:
        try:
            subprocess.run(
                ["git", "init"], capture_output=True, text=True, timeout=10
            )
            git_display = "created new repo"
        except (FileNotFoundError, subprocess.TimeoutExpired):
            git_display = "git not available"

    click.echo(f"  \u2713 OS: {env['os']}")
    stack_display = (
        ", ".join(env["detected_stack"])
        if env["detected_stack"]
        else "none detected"
    )
    click.echo(f"  \u2713 Stack detected: {stack_display}")
    click.echo(f"  \u2713 Git: {git_display}")
    relevant_runtimes = filter_relevant_runtimes(
        env["detected_stack"],
        env["language_runtimes"],
        env["package_managers"],
    )
    runtime_display = (
        ", ".join(relevant_runtimes)
        if relevant_runtimes
        else "none detected"
    )
    click.echo(f"  \u2713 Runtime: {runtime_display}")
    tools_display = (
        ", ".join(env["available_tools"])
        if env["available_tools"]
        else "none detected"
    )
    click.echo(f"  \u2713 Tools: {tools_display}")

    # ------------------------------------------------------------------
    # Prerequisite check — halt if required runtimes/tools missing
    # ------------------------------------------------------------------
    prereq_errors = check_prerequisites(
        detected_stack=env["detected_stack"],
        constraints=objective_data["constraints"],
        runtimes=env["language_runtimes"],
        tools=env["available_tools"],
        pkg_managers=env["package_managers"],
    )
    if prereq_errors:
        for error in prereq_errors:
            click.echo(f"  \u2717 {error}")
        raise SystemExit(1)

    # ------------------------------------------------------------------
    # Environment isolation — stack-aware
    # ------------------------------------------------------------------
    detected_stack = env.get("detected_stack", [])
    needs_python_env = "python" in detected_stack or any(
        "python" in c.lower() for c in objective_data["constraints"]
    )

    project_name = os.path.basename(os.getcwd())
    env_name = f"agentorg-{project_name}"
    env_run_prefix = ""

    if needs_python_env:
        python_version = _detect_python_version(objective_data["constraints"])

        click.echo()
        click.echo("Creating isolated environment...")
        project_env = _create_project_env(env_name, python_version)

        if project_env["type"] == "conda":
            click.echo(
                f"  \u2713 Conda env: {project_env['name']} "
                f"(Python {python_version})"
            )
            env_run_prefix = (
                f"conda run --no-capture-output -n {project_env['name']}"
            )
        elif project_env["type"] == "venv":
            click.echo(
                f"  \u2713 Venv: .venv (Python {python_version})"
            )
            env_run_prefix = (
                f"source {project_env['prefix']}/bin/activate &&"
            )
        else:
            click.echo(f"  \u2717 {project_env['reason']}")
            click.echo(
                "    Install conda or ensure python3 is available and re-run."
            )
            raise SystemExit(1)

        # Write env info for agents to read
        env_info_path = os.path.join(".agentorg", "env")
        os.makedirs(".agentorg", exist_ok=True)
        with open(env_info_path, "w") as f:
            f.write(f"type={project_env['type']}\n")
            f.write(f"name={project_env['name']}\n")
            f.write(f"prefix={project_env['prefix']}\n")
            f.write(f"run_prefix={env_run_prefix}\n")
    else:
        # Non-Python stack — use native build tools (Maven, Gradle, npm, etc.)
        click.echo()
        stack_name = ", ".join(detected_stack) if detected_stack else "detected"
        click.echo(
            f"  \u2713 Environment: {stack_name} project "
            f"\u2014 using native build tools"
        )

        # Write env info indicating native tooling
        env_info_path = os.path.join(".agentorg", "env")
        os.makedirs(".agentorg", exist_ok=True)
        with open(env_info_path, "w") as f:
            f.write("type=native\n")
            f.write(f"name={env_name}\n")
            f.write("prefix=\n")
            f.write("run_prefix=\n")
            f.write(f"stack={','.join(detected_stack)}\n")

    # ------------------------------------------------------------------
    # Touchpoint 4 — Prior run notice
    # ------------------------------------------------------------------
    runs_dir = os.path.join(".agentorg", "runs")
    if os.path.isdir(runs_dir):
        prior_runs = sorted(
            d
            for d in os.listdir(runs_dir)
            if d != "latest" and os.path.isdir(os.path.join(runs_dir, d))
        )
        if prior_runs:
            latest_prior = prior_runs[-1]
            phase_path = os.path.join(runs_dir, latest_prior, "phase-status.md")
            status = "partial"
            if os.path.exists(phase_path):
                with open(phase_path) as f:
                    if "complete" in f.read().lower():
                        status = "complete"
            click.echo()
            click.echo(
                f"Prior run found: {latest_prior} \u2014 {status}"
            )
            click.echo("Starting fresh run. Prior artifacts preserved.")
            click.echo()
            click.echo("Press enter to continue.")
            _wait_for_enter()

    # ------------------------------------------------------------------
    # Touchpoint 5 — Success criteria
    # ------------------------------------------------------------------
    if objective_data["success_criteria"] is None:
        click.echo()
        click.echo("Generating draft success criteria...")
        criteria = _generate_success_criteria(objective_data, env)

        if criteria is None:
            click.echo()
            click.echo("Could not generate draft criteria (API unavailable).")
            click.echo("Add success criteria to objective.md manually,")
            click.echo("then press enter to continue.")
            _wait_for_enter()

            # Re-parse to pick up manual additions
            objective_data = parse_objective("objective.md")
            if objective_data["success_criteria"] is None:
                click.echo("  \u2717 Success criteria still missing.")
                click.echo(
                    "    Add ## Success Criteria with ### Research Phase,"
                )
                click.echo(
                    "    ### Engineering Phase, and ### DevOps Phase sub-sections."
                )
                raise SystemExit(1)
            criteria = objective_data["success_criteria"]
        else:
            _append_success_criteria_to_objective("objective.md", criteria)

        _display_criteria(criteria)
        click.echo()
        click.echo("Edit objective.md to modify these, then press enter")
        click.echo("to confirm and start the run.")
        _wait_for_enter()

        # Re-parse in case user edited
        objective_data = parse_objective("objective.md")
    else:
        criteria = objective_data["success_criteria"]
        click.echo()
        click.echo("Success criteria found in objective.md.")
        _display_criteria(criteria)
        click.echo()
        click.echo("Press enter to confirm and start the run.")
        _wait_for_enter()

        # Re-parse in case user edited while blocking
        objective_data = parse_objective("objective.md")

    # ------------------------------------------------------------------
    # Step 4 — Scaffold
    # ------------------------------------------------------------------
    scaffold_result = create_run_directory(is_greenfield=env["is_greenfield"])
    run_dir = scaffold_result["run_dir"]
    timestamp = scaffold_result["timestamp"]

    # ------------------------------------------------------------------
    # Step 5 — Write init-context.md
    # ------------------------------------------------------------------
    _write_init_context(run_dir, objective_data, env)

    # ------------------------------------------------------------------
    # Step 6 — Populate CLAUDE.md [FIXED] sections
    # ------------------------------------------------------------------
    _populate_claude_md(objective_data, env_run_prefix, env)

    # ------------------------------------------------------------------
    # Step 7 — Copy agent files and schemas
    # ------------------------------------------------------------------
    _copy_agents()
    _copy_schemas()

    # ------------------------------------------------------------------
    # Step 8 — Update budget ledger if cap set
    # ------------------------------------------------------------------
    if objective_data["budget_cap"] is not None:
        ledger_path = os.path.join(run_dir, "budget-ledger.json")
        with open(ledger_path, "r") as f:
            ledger = json.load(f)
        ledger["cap"] = objective_data["budget_cap"]
        ledger["remaining"] = objective_data["budget_cap"]
        with open(ledger_path, "w") as f:
            json.dump(ledger, f, indent=2)

    # ------------------------------------------------------------------
    # Handoff message
    # ------------------------------------------------------------------
    project_type = "greenfield" if env["is_greenfield"] else "existing"
    stack_str = (
        ", ".join(env["detected_stack"])
        if env["detected_stack"]
        else "none"
    )
    budget_str = (
        str(objective_data["budget_cap"])
        if objective_data["budget_cap"]
        else "not set"
    )

    click.echo()
    click.echo("INIT COMPLETE")
    click.echo()
    click.echo(f"Run:            {timestamp}")
    click.echo(f"Environment:    {env['os']}, {stack_str}")
    click.echo(f"Project:        {project_type}")
    click.echo(f"Budget cap:     {budget_str}")
    click.echo()
    click.echo("Next step:")
    click.echo(
        '  claude --agent cto "Read .agentorg/runs/latest/init-context.md and begin the run."'
    )


def doctor() -> None:
    """agentorg doctor — check prerequisites and environment readiness."""
    click.echo(f"agentorg v{__version__}")
    click.echo()
    click.echo("Checking prerequisites...")
    click.echo()

    all_ok = True

    # Python
    import sys

    py_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    if sys.version_info >= (3, 10):
        click.echo(f"  \u2713 Python {py_version}")
    else:
        click.echo(f"  \u2717 Python {py_version} (3.10+ required)")
        all_ok = False

    # Claude Code CLI
    if shutil.which("claude"):
        click.echo("  \u2713 Claude Code CLI")
    else:
        click.echo("  \u2717 Claude Code CLI not found")
        click.echo(
            "    Install: https://docs.anthropic.com/en/docs/claude-code"
        )
        all_ok = False

    # ANTHROPIC_API_KEY
    if os.environ.get("ANTHROPIC_API_KEY"):
        click.echo("  \u2713 ANTHROPIC_API_KEY set")
    else:
        click.echo("  ~ ANTHROPIC_API_KEY not set (optional)")
        click.echo(
            "    Success criteria auto-generation will be unavailable."
        )

    # anthropic SDK
    try:
        import anthropic  # noqa: F401

        click.echo("  \u2713 anthropic SDK installed")
    except ImportError:
        click.echo("  \u2717 anthropic SDK not installed")
        click.echo("    Run: pip install anthropic")
        all_ok = False

    # conda or venv
    if shutil.which("conda"):
        click.echo("  \u2713 conda available")
    else:
        click.echo("  ~ conda not found (will fall back to venv)")

    # git
    if shutil.which("git"):
        click.echo("  \u2713 git available")
    else:
        click.echo("  \u2717 git not found")
        click.echo("    Install git: https://git-scm.com")
        all_ok = False

    # graphify (optional — for existing codebases)
    if shutil.which("graphify"):
        click.echo("  \u2713 graphify available (code knowledge graphs)")
    else:
        click.echo(
            "  ~ graphify not found (optional — improves existing codebase understanding)"
        )
        click.echo(
            "    Install: pip install graphifyy && graphify install"
        )

    # scientific skills (optional — for research agents)
    skills_dir = os.path.expanduser("~/.claude/skills")
    has_sci_skills = (
        os.path.isdir(skills_dir)
        and any(
            "scientific" in d.lower()
            for d in os.listdir(skills_dir)
            if os.path.isdir(os.path.join(skills_dir, d))
        )
    ) if os.path.isdir(skills_dir) else False
    if has_sci_skills:
        click.echo("  \u2713 scientific-agent-skills installed")
    else:
        click.echo(
            "  ~ scientific-agent-skills not found (optional — enhances research)"
        )
        click.echo(
            "    Install: npx skills add K-Dense-AI/scientific-agent-skills"
        )

    # Project files
    click.echo()
    click.echo("Project state:")
    if os.path.exists("objective.template.md"):
        click.echo("  \u2713 objective.template.md present")
    else:
        click.echo("  ~ objective.template.md not found (run agentorg init)")

    if os.path.exists("objective.md"):
        click.echo("  \u2713 objective.md present")
    else:
        click.echo("  \u2717 objective.md not found")
        click.echo("    Create it using objective.template.md as reference.")

    if os.path.exists("CLAUDE.md"):
        click.echo("  \u2713 CLAUDE.md present")
    else:
        click.echo("  ~ CLAUDE.md not found (run agentorg init)")

    if os.path.exists(os.path.join(".claude", "settings.json")):
        click.echo("  \u2713 .claude/settings.json present")
    else:
        click.echo("  ~ .claude/settings.json not found (run agentorg init)")

    click.echo()
    if all_ok:
        click.echo("All prerequisites met.")
    else:
        click.echo("Some prerequisites missing. Fix the above and re-check.")


def start() -> None:
    """agentorg start — full flow: init, wait for objective, run, launch CTO."""
    import time

    click.echo(f"agentorg v{__version__}")
    click.echo()

    # Step 1: Check critical prerequisites
    missing = []
    if not shutil.which("claude"):
        missing.append(
            "Claude Code CLI not found.\n"
            "    Install: https://docs.anthropic.com/en/docs/claude-code"
        )
    if not shutil.which("git"):
        missing.append(
            "git not found.\n"
            "    Install: https://git-scm.com"
        )
    if missing:
        for m in missing:
            click.echo(f"  \u2717 {m}")
        raise SystemExit(1)

    if not os.environ.get("ANTHROPIC_API_KEY"):
        click.echo(
            "  ~ ANTHROPIC_API_KEY not set. "
            "Success criteria auto-generation will be unavailable."
        )

    # Step 2: Run init
    initialise()

    # Step 3: Wait for objective.md
    if not os.path.exists("objective.md"):
        click.echo()
        click.echo(
            "Waiting for objective.md..."
        )
        click.echo(
            "  Create it and drop it into this directory."
        )
        click.echo(
            "  See objective.template.md for the schema."
        )
        click.echo()
        while not os.path.exists("objective.md"):
            time.sleep(2)
        click.echo("  \u2713 objective.md detected!")
        click.echo()
        time.sleep(1)  # let file finish writing

    # Step 4: Run
    run()

    # Step 5: Launch CTO
    click.echo()
    click.echo("Launching CTO agent...")
    click.echo()
    try:
        subprocess.run(
            [
                "claude",
                "--agent", "cto",
                "Read .agentorg/runs/latest/init-context.md and begin the run.",
            ],
        )
    except FileNotFoundError:
        click.echo("  \u2717 Could not launch claude.")
        click.echo(
            "    Run manually: claude --agent cto"
        )
        raise SystemExit(1)


# ---------------------------------------------------------------------------
# Phase detection for resume
# ---------------------------------------------------------------------------

# Ordered list of phases and their key artifacts
_PHASE_ORDER = ["research", "architect", "engineering", "devops"]

_PHASE_ARTIFACTS: dict[str, list[str]] = {
    "research": [
        "handoffs/research-output-manifest.md",
    ],
    "architect": [
        "handoffs/task-breakdown.md",
    ],
    "engineering": [
        "handoffs/engineering-completion-report.md",
    ],
    "devops": [
        "handoffs/deployment-report.md",
    ],
}

_PHASE_DISPLAY = {
    "research": "Research",
    "architect": "Architecture",
    "engineering": "Engineering",
    "devops": "DevOps",
}


def _detect_completed_phases(run_dir: str) -> list[str]:
    """Determine which phases have completed based on artifact presence."""
    completed = []
    for phase in _PHASE_ORDER:
        artifacts = _PHASE_ARTIFACTS[phase]
        if all(
            os.path.exists(os.path.join(run_dir, a)) for a in artifacts
        ):
            completed.append(phase)
        else:
            break  # phases are sequential, stop at first incomplete
    return completed


def _detect_resume_phase(run_dir: str) -> str | None:
    """Determine which phase to resume from.

    Returns the first incomplete phase, or None if all complete.
    """
    completed = _detect_completed_phases(run_dir)
    for phase in _PHASE_ORDER:
        if phase not in completed:
            return phase
    return None


def _discard_phase_artifacts(run_dir: str, from_phase: str) -> list[str]:
    """Remove artifacts from a phase and all subsequent phases.

    Returns list of removed files.
    """
    removed = []
    discard = False
    for phase in _PHASE_ORDER:
        if phase == from_phase:
            discard = True
        if discard:
            for artifact_path in _PHASE_ARTIFACTS[phase]:
                full_path = os.path.join(run_dir, artifact_path)
                if os.path.exists(full_path):
                    os.remove(full_path)
                    removed.append(artifact_path)
            # Also remove phase-specific artifacts (prd-*, adr-*, etc.)
            handoffs = os.path.join(run_dir, "handoffs")
            if phase == "research" and os.path.isdir(handoffs):
                for f in os.listdir(handoffs):
                    if f.startswith(("prd-", "finding-", "research-output")):
                        fp = os.path.join(handoffs, f)
                        os.remove(fp)
                        removed.append(f"handoffs/{f}")
            elif phase == "architect" and os.path.isdir(handoffs):
                for f in os.listdir(handoffs):
                    if f.startswith(("adr-", "task-breakdown")):
                        fp = os.path.join(handoffs, f)
                        os.remove(fp)
                        removed.append(f"handoffs/{f}")
            elif phase == "engineering" and os.path.isdir(handoffs):
                for f in os.listdir(handoffs):
                    if f.startswith("engineering-completion"):
                        fp = os.path.join(handoffs, f)
                        os.remove(fp)
                        removed.append(f"handoffs/{f}")
            elif phase == "devops" and os.path.isdir(handoffs):
                for f in os.listdir(handoffs):
                    if f.startswith(("deployment-brief", "deployment-report")):
                        fp = os.path.join(handoffs, f)
                        os.remove(fp)
                        removed.append(f"handoffs/{f}")
    return removed


def resume(
    timestamp: str | None = None, from_phase: str | None = None
) -> None:
    """agentorg resume — resume a previous run from where it stopped."""
    click.echo(f"agentorg v{__version__}")
    click.echo()

    # ------------------------------------------------------------------
    # Find the run to resume
    # ------------------------------------------------------------------
    runs_dir = os.path.join(".agentorg", "runs")
    if not os.path.isdir(runs_dir):
        click.echo("  \u2717 No runs found. Run agentorg run first.")
        raise SystemExit(1)

    if timestamp:
        run_dir = os.path.join(runs_dir, timestamp)
        if not os.path.isdir(run_dir):
            click.echo(f"  \u2717 Run {timestamp} not found.")
            available = sorted(
                d for d in os.listdir(runs_dir)
                if d != "latest" and os.path.isdir(os.path.join(runs_dir, d))
            )
            if available:
                click.echo(f"    Available runs: {', '.join(available)}")
            raise SystemExit(1)
    else:
        # Use latest
        symlink = os.path.join(runs_dir, "latest")
        if not os.path.islink(symlink):
            click.echo("  \u2717 No latest run found. Run agentorg run first.")
            raise SystemExit(1)
        timestamp = os.readlink(symlink)
        run_dir = os.path.join(runs_dir, timestamp)

    click.echo(f"Resuming run: {timestamp}")
    click.echo()

    # ------------------------------------------------------------------
    # Check for objective.md changes
    # ------------------------------------------------------------------
    init_context_path = os.path.join(run_dir, "init-context.md")
    if not os.path.exists(init_context_path):
        click.echo("  \u2717 init-context.md not found in run directory.")
        click.echo("    This run may be corrupted. Start a fresh run.")
        raise SystemExit(1)

    run_mtime = os.path.getmtime(init_context_path)
    objective_path = "objective.md"
    if not os.path.exists(objective_path):
        click.echo("  \u2717 objective.md not found.")
        raise SystemExit(1)

    objective_mtime = os.path.getmtime(objective_path)
    objective_changed = objective_mtime > run_mtime

    if objective_changed:
        click.echo(
            "  ! objective.md was modified after this run started."
        )
        click.echo(
            "    Existing artifacts may be inconsistent with the "
            "updated objective."
        )
        click.echo()
        click.echo(
            "  Press enter to resume anyway, or Ctrl+C to start fresh "
            "with: agentorg run"
        )
        _wait_for_enter()

        # Re-validate
        errors = validate_objective(objective_path)
        if errors:
            click.echo(f"  \u2717 {errors[0]}")
            raise SystemExit(1)

        # Re-populate CLAUDE.md [FIXED] sections
        objective_data = parse_objective(objective_path)
        env_info_path = os.path.join(".agentorg", "env")
        env_run_prefix = ""
        if os.path.exists(env_info_path):
            with open(env_info_path) as f:
                for line in f:
                    if line.startswith("run_prefix="):
                        env_run_prefix = line.split("=", 1)[1].strip()
        env = scan_environment()
        _populate_claude_md(objective_data, env_run_prefix, env)
        click.echo("  \u2713 CLAUDE.md [FIXED] sections updated")

        # Re-write init-context.md
        _write_init_context(run_dir, objective_data, env)
        click.echo("  \u2713 init-context.md updated")
        click.echo()

    # ------------------------------------------------------------------
    # Detect resume point
    # ------------------------------------------------------------------
    completed = _detect_completed_phases(run_dir)

    if from_phase:
        # User forcing restart from a specific phase
        from_phase = from_phase.lower()
        if from_phase not in _PHASE_ORDER:
            click.echo(f"  \u2717 Unknown phase: {from_phase}")
            click.echo(
                f"    Valid phases: {', '.join(_PHASE_ORDER)}"
            )
            raise SystemExit(1)

        # Discard artifacts from that phase forward
        removed = _discard_phase_artifacts(run_dir, from_phase)
        if removed:
            click.echo(
                f"  Discarding artifacts from "
                f"{_PHASE_DISPLAY[from_phase]} phase forward:"
            )
            for r in removed:
                click.echo(f"    - {r}")
            click.echo()

        resume_phase = from_phase
        # Recompute completed after discard
        completed = _detect_completed_phases(run_dir)
    else:
        resume_phase = _detect_resume_phase(run_dir)

    if resume_phase is None:
        click.echo("  All phases completed. Nothing to resume.")
        click.echo("  To start a fresh run: agentorg run")
        return

    # Display status
    click.echo("Phase status:")
    for phase in _PHASE_ORDER:
        display = _PHASE_DISPLAY[phase]
        if phase in completed:
            click.echo(f"  \u2713 {display} — complete")
        elif phase == resume_phase:
            click.echo(f"  \u25b6 {display} — resuming")
        else:
            click.echo(f"  \u2022 {display} — pending")
    click.echo()

    # ------------------------------------------------------------------
    # Build the resume prompt for CTO
    # ------------------------------------------------------------------
    completed_summary = ""
    if completed:
        completed_names = [_PHASE_DISPLAY[p] for p in completed]
        completed_summary = (
            f"The following phases are already complete: "
            f"{', '.join(completed_names)}. "
            f"Their artifacts are in .agentorg/runs/latest/handoffs/. "
            f"Do NOT regenerate these artifacts. "
        )

    resume_prompt = (
        f"You are resuming run {timestamp}. "
        f"Read .agentorg/runs/latest/init-context.md for full context. "
        f"{completed_summary}"
        f"Resume from the {_PHASE_DISPLAY[resume_phase]} phase. "
        f"Read existing artifacts in handoffs/ before proceeding. "
        f"Continue the lifecycle from Step "
        f"{_PHASE_ORDER.index(resume_phase) * 3 + 2} of your lifecycle loop."
    )

    click.echo(f"Launching CTO agent (resuming from {_PHASE_DISPLAY[resume_phase]})...")
    click.echo()

    try:
        subprocess.run(
            ["claude", "--agent", "cto", resume_prompt],
        )
    except FileNotFoundError:
        click.echo("  \u2717 Could not launch claude.")
        click.echo(
            "    Run manually:"
        )
        click.echo(
            f'    claude --agent cto "{resume_prompt}"'
        )
        raise SystemExit(1)
