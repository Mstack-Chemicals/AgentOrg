# review-report-[task-id]-[cycle].md — Schema

## Review Metadata
task_id: string
cycle: int
reviewer_tier: string
reviewed_commit: string

## Verdict
status: enum[pass, fail]
summary: string

## Issues
issues:
  - id: string
    severity: enum[critical, major, minor]
    location: string
    description: string
    recommendation: string
    acceptance_criterion_ref: string | null

## Acceptance Criteria Check
criteria:
  - criterion: string
    met: bool
    notes: string | null
