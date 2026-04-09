# CLAUDE.md
# Project constitution for agentorg
# [FIXED] sections are written by agentorg run from objective.md
# They are never modified by any agent after init
# Living sections are maintained by the CTO during the run

## [FIXED] Hard Constraints
# Written by agentorg run. Never modified by any agent.
# Every agent must respect these at all times.
# A constraint violation is always severity: critical.
# PLACEHOLDER — populated from objective.md at run time


## [FIXED] Out of Scope
# Written by agentorg run. Never modified by any agent.
# If any agent output touches anything listed here,
# it is a critical violation. Stop and raise BLOCKED.
# PLACEHOLDER — populated from objective.md at run time


## [FIXED] Agent Boundaries
# Written by agentorg run. Never modified.

### What no agent may ever do
- Modify objective.md
- Modify any [FIXED] section in this file
- Skip an escalation level
- Hand off an artifact containing an unresolved blocker
- Fail silently — every failure produces a BLOCKED file
- Retry beyond its defined retry_limit
- Write to a path not listed in its write_paths
- Read decisions.md except the CTO
- Read budget-ledger.json except the CTO
- Write application code except SDE subagents
- Modify src/ except SDE subagents and Engineering Lead
  (Engineering Lead: scaffolding only, never application code)
- Roll back a deployment autonomously
- Patch application code during DevOps phase

### What every agent must do
- Run structural verification as step zero before any work
- Raise BLOCKED immediately if structural verification fails
- Read [FIXED] Hard Constraints and Out of Scope before
  producing any output
- Write to run-log.md after every significant action
- Produce outputs conforming exactly to defined artifact schema
- Escalate to the target defined in their agent spec
- Never skip a level in the escalation chain

## [FIXED] Escalation Chain
# Written by agentorg run. Never modified.

SDE subagents          → Engineering Lead
Reviewer subagents     → Engineering Lead
Engineering Lead       → CTO
Research subagents     → Research Lead
PM subagent            → Research Lead
Research Lead          → CTO
Architect              → CTO
DevOps subagents       → DevOps Lead
DevOps Lead            → CTO
CTO                    → USER

## [FIXED] Filesystem Rules
# Written by agentorg run. Never modified.

All run artifacts:      .agentorg/runs/latest/
Cross-run logs:         .agentorg/logs/
Agent memory:           .agentorg/memory/[agent-name]/
User decisions:         .agentorg/decisions.md
Application code:       APPLICATION_CODE_ROOT_PLACEHOLDER
Agent definitions:      .claude/agents/

No agent creates directories not scaffolded by init.
No agent writes to another agent's memory directory.
No agent reads budget-ledger.json except the CTO.
No agent reads decisions.md except the CTO.

## [FIXED] Handoff Rules
# Written by agentorg run. Never modified.

- No agent hands off with an unresolved blocker
- No agent hands off without running structural
  verification on its own output first
- Research owns what. Architect owns how and in what order.
- Architect's component_order strictly followed by
  Engineering Lead
- Build must be passing before Engineering → CTO handoff
- CI must pass before Deploy subagent is activated
- DevOps never patches application code

## [FIXED] Environment Isolation
# Written by agentorg run. Never modified.
# PLACEHOLDER — populated with env details at run time

## [FIXED] Existing Codebase Rules
# Written by agentorg run. Never modified.
# These rules apply when the project is NOT greenfield.
# If is_greenfield is true in init-context.md, these rules are
# informational only — there is no existing code to preserve.
# PLACEHOLDER — populated with project state at run time

---
# Living sections below — maintained by CTO during the run
---

## Project Context
# Updated by CTO at each phase transition.
# All agents read this for project-level understanding.
# Only CTO writes to this section.

### Stack


### Key Architectural Decisions


### Known Issues


### Current Phase


## Agent Guidelines
# Written by CTO at run start from objective.md and init-context.
# Updated by CTO if new constraints emerge during the run.

### Domain Context


### Stack Conventions


### Key Dependencies


### Testing Conventions

