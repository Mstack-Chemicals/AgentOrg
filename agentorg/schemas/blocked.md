# blocked-[agent-name]-[timestamp].md — Schema

raised_by: string
raised_at: string
phase: string
escalation_target: string

type: enum[ambiguity, missing_input, technical_failure,
           budget_exceeded, repeated_failure,
           external_dependency, constraint_violation]

description: string
context: string
attempts: int

blocks_tasks: string[]
blocks_phase: bool
estimated_cost_if_unresolved: string

options:
  - label: string
    description: string
    tradeoff: string

recommendation: string
rationale: string

response_needed: enum[decision, information, confirmation]
