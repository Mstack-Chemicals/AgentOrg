# Changelog

## 0.2.0 — Feature release

### Added
- `agentorg resume` — resume interrupted runs from where they stopped
  - Detects completed phases by scanning handoff artifacts
  - `--from` flag to restart from a specific phase
  - Warns if objective.md changed mid-run
- `agentorg start` — full automated flow: init, wait for objective, run, launch CTO
- `agentorg doctor` — prerequisite and environment checker
- `start.sh` — one-command launcher script
- Existing codebase support: codebase survey, constitutional rules,
  read-before-write enforcement, existing test preservation
- `## Code Root` field in objective.md for specifying code location
- Stack-aware environment isolation (conda/venv for Python, native for others)
- Runtime prerequisite checks with version validation
- Graphify code knowledge graph integration (optional)
- KDense scientific-agent-skills integration (optional)
- Caveman token reduction support with BLOCKED file exemption (optional)
- SWE-bench evaluation against django__django-16631 (0/19 pass rate task)

### Changed
- Template renamed to `objective.template.md` (schema reference only)
- Goal validation: removed 5-sentence limit, kept paragraph format check
- Agent prompts: added Agent tool to CTO and all leads for subagent spawning
- Agent prompts: added existing codebase principles to SDE, Architect, Reviewer
- Agent prompts: CTO research-brief requires internal API discovery questions
- SDE agents: new principle to search for existing APIs before custom logic
- Reviewer checklist: existing internal API usage check
- Environment scan: code-root-aware stack and git detection
- CLI handoff message: prints exact working claude command

### Fixed
- Claude CLI invocation: use positional arg, not --prompt flag
- Version regex: word boundary prevents "Django" matching "go"
- Scaffold: no src/ creation for existing codebases
- Agent spec references: spec/ paths replaced with .agentorg/schemas/

## 0.1.0 — Initial release

First public release of agentorg.

### Included
- CTO orchestrator
- Research org: Research Lead, Researcher, PM
- Architect
- Engineering org: Engineering Lead, SDE1, SDE2, SDE3, Reviewer
- DevOps org: DevOps Lead, CI Agent, Deploy Agent
- Full escalation protocol
- Budget governor with estimation pass
- Init flow with objective.md validation and env scan
- CLI: agentorg init, agentorg run, agentorg version
