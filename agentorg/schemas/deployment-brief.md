# deployment-brief.md — Schema

## Deployment Context
goal_summary: string

## Codebase Handoff
branch: string
last_commit: string
test_coverage: string
build_status: enum[passing]

## Deployment Target
environment: string
infrastructure: string[]

## Success Criteria
criteria:
  - criterion: string
    verification_method: string

## Rollback Condition
rollback_triggers: string[]

## Budget Allocation
token_budget: int | null
