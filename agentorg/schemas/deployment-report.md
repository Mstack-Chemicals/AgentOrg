# deployment-report.md — Schema

## Status
overall: enum[pass, fail]

## CI Results
ci_status: enum[pass, fail]
ci_output: string
commit_verified: string

## Deployment Results
deployment_status: enum[pass, fail]
environment: string
deployed_at: string
deployment_notes: string | null

## Success Criteria Verification
criteria:
  - criterion: string
    met: bool
    verification_method: string
    evidence: string

## Infrastructure State
infrastructure:
  - component: string
    status: enum[healthy, degraded, missing]
    version: string | null
    notes: string | null

## Rollback Status
rollback_required: bool
rollback_reason: string | null

## Budget Consumed
tokens_used: int
tokens_remaining: int | null
