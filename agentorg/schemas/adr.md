# adr-[id].md — Schema

## Context
prd_ref: string
problem_statement: string

## Decisions
decisions:
  - id: string
    question: string
    decision: string
    rationale: string
    alternatives_considered:
      - option: string
        reason_rejected: string
    reversible: bool

## Implications
new_constraints: string[]
risks: string[]

## Component Boundaries
inputs: string[]
outputs: string[]
interfaces:
  - component: string
    method: string
    contract: string
