# agentorg

## Description

agentorg is a structured multi-agent system for building production-grade software on real codebases, not just greenfield demos. Instead of loosely coordinated “bags of agents,” it enforces a strict lifecycle — Research, Architecture, Engineering, DevOps — where every phase produces schema-validated artifacts that must pass verification gates before progressing. Governed by a constitutional rule set and a central CTO agent that validates decisions, manages budget, and prevents error propagation, agentorg closes the planner-coder gap and ensures reliable handoffs between agents. The result is a disciplined, cost-aware orchestration framework that turns autonomous agents into a coherent, production-ready engineering pipeline.

Drop in an objective. Run one command. Get working software.

## Quick start

```bash
pip install agentorg

cd your-project
agentorg start
```

That's it. `agentorg start` will:
1. Create `objective.template.md` (schema reference) and project config
2. Wait for you to create `objective.md`
3. Validate, scan your environment, check prerequisites
4. Scaffold the run and launch the CTO agent

### Creating objective.md

`objective.md` is the only file you write. Use `objective.template.md` as the
schema reference. You can create it however you want:

- Write it manually
- Paste your existing PRD into ChatGPT/Claude and ask it to convert
- Use any AI tool with the template as a schema guide

Required sections: **Goal**, **Constraints**, **Out of Scope**.
Optional: **Success Criteria**, **Code Root**, **Budget Cap**, **Notes**.

```markdown
## Goal
Build a REST API that serves weather data from a PostgreSQL database.

## Constraints
- Python 3.11 only
- Must use existing PostgreSQL database

## Out of Scope
- No frontend
- No production deployment

## Code Root
backend/

## Budget Cap
100000
```

Drop `objective.md` into your project directory and `agentorg start` picks it up.

## Works with existing codebases

agentorg isn't limited to greenfield projects. Point it at an existing codebase
and it will read, understand, and build on top of it:

1. Clone your repo into the project directory
2. Set `## Code Root` in objective.md to the repo folder (e.g. `myapp/`)
3. Run `agentorg start`

The system surveys the existing architecture, follows existing patterns, and
runs existing tests after every change to ensure nothing breaks.

If [Graphify](https://github.com/safishamsi/graphify) is installed, the CTO
automatically builds a code knowledge graph before the run starts, giving
every downstream agent a structural map of the codebase.

## How it works

```
You create objective.md
         |
agentorg start validates and scans your environment
         |
CTO orchestrates the full lifecycle:
  Research Lead  -> PRDs
  Architect      -> ADRs + Task Breakdown
  Engineering Lead -> SDE subagents -> Code + Reviews
  DevOps Lead    -> CI + Deploy
         |
Working software
```

## The org chart

```
CTO (Opus)
+-- Research Lead (Opus)
|   +-- Researcher subagents (Sonnet)
|   +-- PM subagent (Sonnet)
+-- Architect (Opus)
+-- Engineering Lead (Opus)
|   +-- SDE1 subagents (Sonnet) -- simple tasks
|   +-- SDE2 subagents (Sonnet) -- moderate tasks
|   +-- SDE3 subagents (Opus)   -- complex tasks
|   +-- Reviewer subagents (Opus)
+-- DevOps Lead (Opus)
    +-- CI subagent (Sonnet)
    +-- Deploy subagent (Sonnet)
```

## CLI commands

```
agentorg start     Full flow: init, wait for objective, run, launch CTO
agentorg init      Create template and config files only
agentorg run       Validate and scaffold only (no CTO launch)
agentorg resume    Resume a previous run from where it stopped
agentorg doctor    Check all prerequisites
agentorg version   Print version
```

### Running manually (step by step)

If `agentorg start` doesn't suit your workflow, you can run each step yourself:

```bash
agentorg init                  # creates template + config files
# ... create objective.md ...
agentorg run                   # validate, scan, scaffold
claude --agent cto "Read .agentorg/runs/latest/init-context.md and begin the run."
```

The last command launches Claude Code with the CTO agent and passes the
initial prompt as a positional argument. The CTO reads the init context and
autonomously orchestrates the full lifecycle.

## Resuming a run

If a run is interrupted — user cancellation, error, or you need to fix your
objective — resume from where it stopped:

```bash
agentorg resume                        # resume latest run
agentorg resume 20260413T120520        # resume a specific run
agentorg resume --from architect       # restart from a specific phase
```

The system detects which phases completed by checking for handoff artifacts.
If `objective.md` was modified after the run started, it warns you and
re-validates before continuing.

The `--from` flag discards artifacts from that phase forward and restarts
from there. Useful when Research was fine but Architecture needs a redo.

## Prerequisites

- Python 3.10+
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) installed and authenticated
- `ANTHROPIC_API_KEY` set (for success criteria auto-generation)

Run `agentorg doctor` to check everything:

```
$ agentorg doctor

agentorg v0.1.0

Checking prerequisites...

  ok  Python 3.12.7
  ok  Claude Code CLI
  ok  ANTHROPIC_API_KEY set
  ok  anthropic SDK installed
  ok  conda available
  ok  git available
  ok  graphify available
  ok  scientific-agent-skills installed
```

### Optional tools

These are not required but significantly improve results:

- **[Graphify](https://github.com/safishamsi/graphify)** — builds a knowledge graph
  of your codebase so agents understand module relationships, god nodes, and
  cross-cutting connections without reading every file. Especially valuable for
  large existing codebases (500+ files). Install: `pip install graphifyy && graphify install`

- **[Scientific Agent Skills](https://github.com/K-Dense-AI/scientific-agent-skills)** —
  135 pre-built skills giving Research agents structured access to 78+ scientific
  databases (PubChem, ChEMBL, UniProt, etc.) and 70+ optimized Python packages
  (RDKit, Scanpy, BioPython, etc.). Install: `npx skills add K-Dense-AI/scientific-agent-skills`

## Environment isolation

- **Python projects**: agentorg creates an isolated conda env (or venv fallback)
  automatically. All agent commands run inside it.
- **Java/Node/Go/Rust projects**: native build tools are used directly.
  agentorg detects the stack and skips Python env creation.

## Runtime prerequisite checks

Before engineering starts, agentorg verifies that the required runtimes and
build tools are installed. A Java project without `java` or `mvn` on PATH
will halt immediately with install instructions — not fail 30 minutes into
the engineering phase.

## For developers

All agent definitions are in `.claude/agents/` after a run.
You can inspect and modify them.

Run `agentorg init` to see the full template schema in `objective.template.md`.

## Roadmap

- `agentorg inspect` -- browse prior run artifacts
- Fast-track mode for small tasks (compressed phases, not skipped)
- Parallel orgs for multi-repo objectives
- Formal complexity rubric
- Architect subagents for large PRD sets

## License

MIT
