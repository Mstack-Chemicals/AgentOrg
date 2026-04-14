# agentorg v0.1.0 — Release Notes

## The landscape

There are several tools that use AI agents to write software. Here's what
exists and how they work.

### Claude Code Agent Teams (Anthropic)

- **Subagent spawning**: A parent agent spawns isolated child agents, each
  with its own 200K-token context window, defined as Markdown files in
  `.claude/agents/`. The child runs independently and returns only its
  final output.
- **Two coordination modes**: Subagents are hierarchical (parent-child).
  Agent Teams (experimental) are peer-to-peer with a shared task list and
  mailbox messaging.
- **No built-in orchestration**: The Agent tool is a primitive. There is no
  task decomposition, phase sequencing, artifact validation, or escalation
  protocol. All orchestration logic must be authored in the system prompt.

### Paperclip (paperclipai)

- **AI company simulation**: A CEO agent receives a mission and delegates to
  Manager and Worker agents in a corporate hierarchy. Built on Claude Code
  as the execution engine. 30K+ GitHub stars in three weeks.
- **File-based communication**: Agents read and write to a shared filesystem.
  No custom protocol — simple but limits real-time coordination.
- **Fully autonomous framing**: Designed for "zero-human companies." Task
  checkout and budget enforcement prevent double-work and runaway spend,
  but there are no structured verification gates between phases.

### Cursor / Windsurf / IDE tools

- **IDE-native AI**: Full VS Code forks with semantic codebase indexing,
  multi-file refactoring, and inline completions. Cursor supports 8
  parallel agents; Windsurf's Cascade performs autonomous multi-step
  task planning.
- **Single-agent architecture**: These are sophisticated coding assistants,
  not multi-agent orchestration systems. They excel at edit-level tasks
  within an IDE session but don't manage research, architecture, reviews,
  or deployment as distinct phases.
- **No persistent project structure**: No run artifacts, no handoff
  schemas, no cross-run memory. Each session starts fresh.

### MetaGPT / ChatDev

- **Software company simulation**: Predefined roles (Product Manager,
  Architect, Engineer, QA) pipeline tasks through a waterfall process.
  MetaGPT achieved 85.9% Pass@1 on code generation benchmarks.
- **Rigid pipeline**: Opinionated structure reduces glue code but makes
  customisation hard. Designed for greenfield generation, not integration
  with existing codebases.
- **Academic origin**: Strong on benchmarks, weaker on production use
  with real repositories, real dependencies, and real deployment targets.

### OpenHands / Devin

- **Sandboxed execution**: OpenHands runs agents in Docker containers with
  full shell, browser, and Python access. Devin operates as a cloud-based
  autonomous agent via Slack/Teams.
- **Single-agent focused**: While OpenHands supports hierarchical delegation,
  multi-agent coordination is minimal. Devin's 67% PR merge rate (up from
  34%) shows improvement but still fails on complex end-to-end tasks.
- **No project-level decomposition**: Both excel at step-by-step task
  execution but lack higher-level planning that breaks a large project into
  coordinated phases with verified handoffs.

---

## What agentorg does

### 1. Structured lifecycle with verified phase transitions

agentorg enforces a strict sequence: Research, Architecture, Engineering,
DevOps. Each phase produces schema-defined artifacts (research briefs, PRDs,
ADRs, task breakdowns, completion reports) that are structurally verified
before the next phase begins. A malformed artifact halts the pipeline — it
cannot be passed downstream. This is the architectural choice that Google
DeepMind's research identifies as reducing error amplification from 17x
(unstructured multi-agent networks) to 4.4x (centralized orchestrator with
validation gates).

### 2. Constitutional governance with escalation protocol

Every agent operates under a constitution (CLAUDE.md) with immutable
`[FIXED]` sections: hard constraints, out-of-scope boundaries, agent
permissions, filesystem rules, and handoff rules. No agent can modify these.
When an agent is stuck, it doesn't fail silently or push forward with a
guess — it writes a structured BLOCKED file with options and escalates
through a defined chain (Subagent -> Lead -> CTO -> User). The user only
sees decisions that the system genuinely cannot resolve on its own.

### 3. Works on existing codebases, not just greenfield

Most multi-agent coding tools assume a blank slate. agentorg detects
existing project structure, surveys the codebase before any agent writes
code, and enforces rules that preserve existing functionality: read before
write, follow existing patterns, run existing tests after every change.
The CTO produces a codebase summary that flows through every phase so no
agent operates blind. A `Code Root` field in objective.md lets the user
point the system at any directory structure.

---

## Why this approach

### The problem with "bags of agents"

Google DeepMind's December 2025 study ("Towards a Science of Scaling Agent
Systems") found that unstructured multi-agent networks amplify errors up to
17.2x compared to single-agent baselines. Without validation between agents,
errors cascade unchecked. Adding more agents doesn't help — it multiplies
failure modes.

A separate study on the "Planner-Coder Gap" (arXiv 2510.10460) showed that
semantically equivalent inputs cause drastic performance drops in multi-stage
systems. Information is lost at every handoff: planning agents produce
underspecified plans, coding agents misinterpret intent during implementation.
The gap between "what was planned" and "what gets coded" is the primary
failure mode.

The industry data confirms this. Google's 2025 DORA report found that 90%
AI adoption correlated with 9% more bugs, 91% more code review time, and
154% larger PRs. More AI doesn't automatically mean better software.

### What agentorg does differently

**Structured artifacts instead of free-form messages.** Every phase
transition produces a schema-defined document. A research brief isn't "some
notes" — it has required fields, traced questions, and a structural
verification checklist. A task breakdown isn't a to-do list — it has
complexity classifications, dependency graphs, acceptance criteria, and
integration points. This directly addresses the planner-coder gap: the
Architect's output is precise enough that an SDE agent can implement it
without guessing intent.

**A CTO that validates, not just routes.** The CTO agent doesn't simply
pass artifacts from one phase to the next. It runs structural verification
at every transition, checks for unresolved blockers, manages the budget
ledger, and writes to a decisions log so it never asks the user the same
question twice. It's a validation bottleneck by design — the chokepoint
that catches errors before they compound.

**Tiered model assignment.** Not every task needs the most expensive model.
Research leads and architects run on Opus (deep reasoning). SDE1 workers
run on Sonnet (fast execution for simple tasks). SDE3 workers run on Opus
(complex tasks that need architectural awareness). Reviewers run on Opus
(catching subtle issues requires strong reasoning). This isn't just cost
optimisation — it's matching model capability to task complexity, which
the research shows matters more than throwing compute at everything.

**Budget governance as a first-class concern.** Before engineering starts,
the CTO runs an estimation pass: counts tasks by complexity, multiplies by
cost constants, presents a range to the user. The user can proceed, adjust
scope, or set a cap. During execution, the CTO checks the budget before
every agent invocation. This is not an afterthought — it's step 6 of a
12-step lifecycle, and the system will not proceed to engineering without
user confirmation.

**Constitutional constraints, not suggestions.** CLAUDE.md contains
`[FIXED]` sections that no agent can modify. Hard constraints, out-of-scope
boundaries, and agent permissions are written once at init and enforced
throughout the run. This is qualitatively different from "please follow
these guidelines" — it's a governance layer that every agent reads before
producing any output. A constraint violation is always severity: critical.

### The principle

The systems that work in practice are not "bags of agents." They are tightly
structured pipelines with clear artifact boundaries, explicit verification
at every handoff, and human oversight at critical junctures. agentorg is
built on this principle: the orchestration structure matters more than the
number of agents, and every phase transition is a quality gate, not a
message relay.
