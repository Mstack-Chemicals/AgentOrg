# Budget Governor — Constitution Reference

This document is the authoritative source for budget rules.
Reproduced from spec/06-budget-governor.md for agent reference.

## Hard Rules

- Only CTO reads and writes budget-ledger.json
- Budget ledger updated after every agent invocation
- Estimation pass mandatory before Engineering begins
- User must respond to estimation pass before Engineering starts
- Cap enforcement checks happen before every agent invocation
- Tier downgrades from budget pressure logged to
  task-deviations.log with reason: budget_constraint
- Budget decisions made by user written to decisions.md
- CTO never skips a task for budget reasons without logging

## Budget Ledger Location

.agentorg/runs/latest/budget-ledger.json

## Cost Constants Reference

CTO:                        20.0
Research Lead:              20.0
Researcher subagent:         4.0
PM subagent:                 5.0
Architect (full pass):      20.0
Architect (revision pass):   5.0
Engineering Lead:           20.0
SDE1 subagent:               1.0
SDE2 subagent:               4.0
SDE3 subagent:              10.0
Reviewer subagent:          20.0
DevOps Lead:                15.0
CI subagent:                 4.0
Deploy subagent:             4.0

## Full format reference

See spec/06-budget-governor.md
