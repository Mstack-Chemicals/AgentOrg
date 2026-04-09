# agentorg

A multi-agent development system built on Claude Code.
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
agentorg doctor    Check all prerequisites
agentorg version   Print version
```

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
```

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

## V2 roadmap

- `agentorg resume` -- resume from prior run
- `agentorg inspect` -- browse prior run artifacts
- Formal complexity rubric
- Architect subagents for large PRD sets

## License

MIT
