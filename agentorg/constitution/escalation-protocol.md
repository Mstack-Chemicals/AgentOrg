# Escalation Protocol — Constitution Reference

This document is the authoritative source for escalation rules.
Reproduced from spec/05-escalation-protocol.md for agent reference.
All agents must follow these rules without exception.

## Escalation Chain

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

## Hard Rules

- No agent skips an escalation level
- No agent fails silently — every failure produces a BLOCKED file
- No agent retries beyond its retry_limit
- CTO checks decisions.md before every user escalation
- CTO never asks the user the same question twice
- Reviewer retry_limit is 0 — produce report and stop
- Third consecutive Reviewer fail on same task →
  Engineering Lead raises BLOCKED to CTO
- Rollback is never a silent DevOps decision
- DevOps never patches application code
- No agent hands off with an unresolved blocker

## BLOCKED File Location

.agentorg/runs/latest/blocked/blocked-[agent-name]-[timestamp].md

## Full format reference

See spec/05-escalation-protocol.md
