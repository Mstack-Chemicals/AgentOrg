# task-breakdown.md — Schema

## Architecture Summary
overview: string
component_order: string[]

## Tasks
tasks:
  - id: string
    title: string
    description: string
    adr_ref: string
    prd_requirements: string[]
    complexity: enum[simple, moderate, complex]
    depends_on: string[]
    acceptance_criteria: string[]

## Integration Points
integrations:
  - task_a: string
    task_b: string
    nature: string
    validation: string

## Open Questions
questions:
  - question: string
    impact: enum[high, low]
    recommendation: string
    affects_tasks: string[]

## Budget Consumed
tokens_used: int
tokens_remaining: int | null
