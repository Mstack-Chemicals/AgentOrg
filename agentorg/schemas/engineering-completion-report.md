# engineering-completion-report.md — Schema

## Status
overall: enum[pass]

## Task Summary
tasks:
  - id: string
    title: string
    status: enum[complete, skipped, added]
    assigned_tier: enum[sde1, sde2, sde3]
    complexity_actual: enum[simple, moderate, complex]
    files_affected: string[]
    acceptance_criteria_met: string[]
    retry_count: int

## Sequence Adherence
component_order_followed: bool
deviations: string[]

## Integration Validation
integrations:
  - task_a: string
    task_b: string
    validation_result: enum[pass]
    notes: string | null

## Review Summary
total_review_cycles: int
issues_raised: int
issues_resolved: int
outstanding_issues: string[]

## Engineering Success Criteria
criteria:
  - criterion: string
    met: bool
    evidence: string

## Codebase State
branch: string
last_commit: string
test_coverage: string
build_status: enum[passing]

## Budget Consumed
tokens_used: int
tokens_remaining: int | null
