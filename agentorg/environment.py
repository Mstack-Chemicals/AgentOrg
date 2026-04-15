"""Scan the local environment for OS, runtimes, tools, and project state."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess


def _check_binaries(names: list[str]) -> list[str]:
    """Return the subset of binary names that exist on PATH."""
    return [n for n in names if shutil.which(n)]


def _git_config(key: str) -> str:
    """Read a git config value, return empty string on failure."""
    try:
        result = subprocess.run(
            ["git", "config", key],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return ""


def _detect_stack(search_dirs: list[str] | None = None) -> list[str]:
    """Infer tech stack from files in the given directories.

    Checks the current directory and any additional search_dirs.
    """
    dirs_to_check = ["."]
    if search_dirs:
        dirs_to_check.extend(search_dirs)

    all_entries: set[str] = set()
    for d in dirs_to_check:
        if os.path.isdir(d):
            all_entries.update(os.listdir(d))

    stack: list[str] = []

    if "package.json" in all_entries:
        stack.append("node")
        if "tsconfig.json" in all_entries:
            stack.append("typescript")
    if any(
        f in all_entries
        for f in ("pyproject.toml", "setup.py", "requirements.txt")
    ):
        stack.append("python")
    if "Cargo.toml" in all_entries:
        stack.append("rust")
    if "go.mod" in all_entries:
        stack.append("go")
    if "pom.xml" in all_entries or "build.gradle" in all_entries:
        stack.append("java")
    if "Gemfile" in all_entries:
        stack.append("ruby")
    if "Dockerfile" in all_entries or "docker-compose.yml" in all_entries:
        stack.append("docker")

    return stack


def _describe_structure() -> str:
    """Describe the top-level project structure."""
    agentorg_paths = {
        "objective.md",
        "CLAUDE.md",
        ".claude",
        ".agentorg",
        ".git",
        ".DS_Store",
    }
    entries = os.listdir(".")
    project_entries = [e for e in entries if e not in agentorg_paths]
    if not project_entries:
        return "none"
    return ", ".join(sorted(project_entries)[:15])


def _detect_code_root() -> str:
    """Detect the root directory of existing application code.

    Looks for project markers (source code indicators) in the current
    directory and its immediate subdirectories. Returns the path relative
    to cwd where the existing code lives.
    """
    agentorg_paths = {
        "objective.md", "CLAUDE.md", ".claude", ".agentorg",
        ".git", ".DS_Store", ".venv", "src",
    }

    # Check if project markers exist at the top level (code is here)
    top_level_markers = {
        "pyproject.toml", "setup.py", "setup.cfg", "requirements.txt",
        "package.json", "Cargo.toml", "go.mod", "pom.xml",
        "build.gradle", "Gemfile", "Makefile", "CMakeLists.txt",
    }
    entries = set(os.listdir(".")) if os.path.isdir(".") else set()

    if entries & top_level_markers:
        return "./"

    # Check immediate subdirectories for project markers or .git
    for entry in sorted(entries - agentorg_paths):
        entry_path = os.path.join(".", entry)
        if not os.path.isdir(entry_path):
            continue
        try:
            sub_entries = set(os.listdir(entry_path))
        except PermissionError:
            continue
        # If subdirectory has project markers or its own .git, it's the code root
        if sub_entries & (top_level_markers | {".git"}):
            return f"{entry}/"
        # If it contains source-like directories (src, lib, app, etc.)
        source_dirs = {"src", "lib", "app", "pkg", "cmd"}
        if sub_entries & source_dirs:
            return f"{entry}/"

    # Fallback: use current directory
    return "./"


def _get_runtime_version(binary: str) -> str | None:
    """Get the version string of a runtime binary. Returns None if unavailable."""
    # Different runtimes use different flags and output formats
    version_flags = {
        "java": ["-version"],      # outputs to stderr
        "javac": ["-version"],
        "node": ["--version"],
        "python3": ["--version"],
        "python": ["--version"],
        "go": ["version"],
        "rustc": ["--version"],
        "ruby": ["--version"],
    }
    flags = version_flags.get(binary, ["--version"])

    try:
        result = subprocess.run(
            [binary] + flags,
            capture_output=True,
            text=True,
            timeout=10,
        )
        output = result.stdout.strip() or result.stderr.strip()
        if output:
            return output.split("\n")[0]
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


# -- Stack prerequisite definitions --
# Maps stack name to required (runtime_binaries, build_tool_binaries, install_hint)
# At least one runtime binary and one build tool binary must be present.
_STACK_PREREQUISITES: dict[str, dict] = {
    "java": {
        "runtimes": ["java", "javac"],
        "build_tools": ["mvn", "gradle"],
        "runtime_hint": "Install a JDK (e.g. OpenJDK 17+): https://adoptium.net",
        "build_hint": "Install Maven (mvn) or Gradle",
    },
    "node": {
        "runtimes": ["node"],
        "build_tools": ["npm", "yarn", "pnpm"],
        "runtime_hint": "Install Node.js: https://nodejs.org",
        "build_hint": "Install npm, yarn, or pnpm",
    },
    "rust": {
        "runtimes": ["rustc"],
        "build_tools": ["cargo"],
        "runtime_hint": "Install Rust: https://rustup.rs",
        "build_hint": "Install Rust (includes cargo): https://rustup.rs",
    },
    "go": {
        "runtimes": ["go"],
        "build_tools": ["go"],
        "runtime_hint": "Install Go: https://go.dev/dl",
        "build_hint": "Install Go: https://go.dev/dl",
    },
    "ruby": {
        "runtimes": ["ruby"],
        "build_tools": ["bundle", "gem"],
        "runtime_hint": "Install Ruby: https://www.ruby-lang.org",
        "build_hint": "Install Bundler: gem install bundler",
    },
    "python": {
        "runtimes": ["python3", "python"],
        "build_tools": ["pip", "pip3"],
        "runtime_hint": "Install Python 3.10+: https://www.python.org",
        "build_hint": "Install pip (usually included with Python)",
    },
}


def _parse_version_number(version_str: str) -> str | None:
    """Extract a version number like '17.0.2' or '3.11.5' from a version string."""
    import re

    match = re.search(r"(\d+)(?:\.(\d+))?(?:\.(\d+))?", version_str)
    if match:
        parts = [p for p in match.groups() if p is not None]
        return ".".join(parts)
    return None


def _extract_required_version(constraints: list[str], language: str) -> str | None:
    """Extract a version requirement from constraints for a given language.

    Handles patterns like 'Java 17', 'Python 3.11+', 'Node >= 18', 'Go 1.21'.
    Returns the minimum version string or None.
    """
    import re

    for c in constraints:
        # Match patterns like "Java 17", "Python 3.11+", "Node >= 18"
        # Word boundary (\b) prevents "Django" matching "go"
        pattern = rf"(?i)\b{language}\s*[>=]*\s*([\d]+(?:\.[\d]+)*)"
        m = re.search(pattern, c)
        if m:
            return m.group(1)
    return None


def _version_at_least(installed: str, required: str) -> bool:
    """Check if installed version >= required version."""
    def _to_tuple(v: str) -> tuple[int, ...]:
        return tuple(int(x) for x in v.split("."))

    try:
        return _to_tuple(installed) >= _to_tuple(required)
    except (ValueError, TypeError):
        return True  # can't parse, don't block


def check_prerequisites(
    detected_stack: list[str],
    constraints: list[str],
    runtimes: list[str],
    tools: list[str],
    pkg_managers: list[str],
) -> list[str]:
    """Check that required runtimes and build tools are installed.

    Returns a list of error strings. Empty list means all prerequisites met.
    Each error includes the exact install instruction.
    """
    errors: list[str] = []
    all_binaries = set(runtimes + tools + pkg_managers)

    for stack_name in detected_stack:
        prereqs = _STACK_PREREQUISITES.get(stack_name)
        if not prereqs:
            continue

        # Check runtime
        has_runtime = any(r in all_binaries for r in prereqs["runtimes"])
        if not has_runtime:
            errors.append(
                f"Runtime missing: {stack_name} project detected but "
                f"no {stack_name} runtime found\n"
                f"    {prereqs['runtime_hint']}"
            )
            continue  # no point checking build tools if runtime is missing

        # Check build tool
        has_build_tool = any(t in all_binaries for t in prereqs["build_tools"])
        if not has_build_tool:
            errors.append(
                f"Build tool missing: {stack_name} project detected but "
                f"no build tool found\n"
                f"    {prereqs['build_hint']}"
            )

        # Check version if constraint specifies one
        # Map stack names to language names for constraint matching
        lang_names = {
            "java": "java", "node": "node", "python": "python",
            "go": "go", "rust": "rust", "ruby": "ruby",
        }
        lang = lang_names.get(stack_name, stack_name)
        required_version = _extract_required_version(constraints, lang)

        if required_version:
            # Find the installed runtime and check its version
            for rt in prereqs["runtimes"]:
                if rt in all_binaries:
                    version_output = _get_runtime_version(rt)
                    if version_output:
                        installed_version = _parse_version_number(version_output)
                        if installed_version and not _version_at_least(
                            installed_version, required_version
                        ):
                            errors.append(
                                f"Version mismatch: {stack_name} {installed_version} "
                                f"installed but {required_version}+ required\n"
                                f"    Update {rt} to version {required_version} "
                                f"or higher."
                            )
                    break  # only check the first available runtime

    # Also check constraints that mention a language not in detected_stack
    # (e.g. user specifies "Java 17 only" but stack detection missed it)
    for lang, prereqs in _STACK_PREREQUISITES.items():
        if lang in detected_stack:
            continue  # already checked above
        required_version = _extract_required_version(constraints, lang)
        if required_version:
            has_runtime = any(r in all_binaries for r in prereqs["runtimes"])
            if not has_runtime:
                errors.append(
                    f"Runtime missing: constraints require {lang} "
                    f"{required_version}+ but {lang} is not installed\n"
                    f"    {prereqs['runtime_hint']}"
                )

    return errors


# Maps stack names to their relevant runtime/tool binaries for display filtering
_STACK_RELEVANT_BINARIES: dict[str, set[str]] = {
    "java": {"java", "javac", "mvn", "gradle"},
    "node": {"node", "npm", "yarn", "pnpm", "npx"},
    "typescript": {"node", "npm", "yarn", "pnpm", "npx", "tsc"},
    "python": {"python3", "python", "pip", "pip3"},
    "rust": {"rustc", "cargo"},
    "go": {"go"},
    "ruby": {"ruby", "bundle", "gem"},
    "docker": {"docker", "docker-compose"},
}


def filter_relevant_runtimes(
    detected_stack: list[str],
    runtimes: list[str],
    pkg_managers: list[str],
) -> list[str]:
    """Filter runtimes and tools to only those relevant to the detected stack."""
    if not detected_stack:
        return runtimes  # no stack detected, show everything

    relevant_bins: set[str] = set()
    for stack_name in detected_stack:
        relevant_bins.update(_STACK_RELEVANT_BINARIES.get(stack_name, set()))

    all_available = set(runtimes + pkg_managers)
    filtered = [r for r in runtimes if r in relevant_bins]

    return filtered if filtered else runtimes  # fallback to all if nothing matched


def scan_environment() -> dict:
    """Scan the current environment and return a structured dict.

    Returns a dict matching the init-context.md Environment + Project State schema.
    """
    # OS
    os_info = f"{platform.system()} {platform.release()}"

    # Shell
    shell_path = os.environ.get("SHELL", "")
    shell = os.path.basename(shell_path) if shell_path else "unknown"

    # Language runtimes
    runtimes = _check_binaries(
        ["python3", "python", "node", "ruby", "go", "rustc", "java"]
    )

    # Package managers
    pkg_managers = _check_binaries(
        ["pip", "pip3", "npm", "yarn", "pnpm", "cargo", "go", "mvn", "gradle", "bundle"]
    )

    # Git config
    git_user_name = _git_config("user.name")
    git_user_email = _git_config("user.email")
    if git_user_name and git_user_email:
        git_user = f"{git_user_name} <{git_user_email}>"
    elif git_user_name:
        git_user = git_user_name
    else:
        git_user = "not configured"

    git_default_branch = _git_config("init.defaultBranch") or "main"

    # Available tools
    tools = _check_binaries(
        ["docker", "kubectl", "terraform", "aws", "gcloud", "az", "helm", "make", "cmake"]
    )

    # Project state
    agentorg_paths = {
        "objective.md",
        "CLAUDE.md",
        ".claude",
        ".agentorg",
        ".git",
        ".DS_Store",
    }
    entries = set(os.listdir(".")) if os.path.isdir(".") else set()
    non_agentorg = entries - agentorg_paths
    is_greenfield = len(non_agentorg) == 0

    existing_structure = _describe_structure()

    # Determine code root
    if is_greenfield:
        code_root = "src/"
    else:
        code_root = _detect_code_root()

    # Detect stack — check both cwd and code root
    search_dirs = [code_root.rstrip("/")] if code_root not in ("./", "src/") else []
    detected_stack = _detect_stack(search_dirs)

    # Check if git repo exists in code root or cwd
    git_exists_in_code_root = (
        os.path.isdir(os.path.join(code_root.rstrip("/"), ".git"))
        if code_root not in ("./",)
        else False
    )
    has_git = os.path.isdir(".git") or git_exists_in_code_root

    return {
        "os": os_info,
        "shell": shell,
        "language_runtimes": runtimes,
        "package_managers": pkg_managers,
        "git_config": {
            "user": git_user,
            "default_branch": git_default_branch,
        },
        "available_tools": tools,
        "is_greenfield": is_greenfield,
        "existing_structure": existing_structure,
        "detected_stack": detected_stack,
        "code_root": code_root,
        "has_git": has_git,
    }
