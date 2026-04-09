# prd-[id].md — Schema

## Component
name: string
scope: string

## Problem Statement
what_we_are_solving: string
why_it_matters: string

## Findings
background: string
data_requirements: string[]
external_dependencies: string[]
known_constraints: string[]

## Functional Requirements
requirements:
  - id: string
    description: string
    priority: enum[must, should, could]

## Non-Functional Requirements
performance: string | null
scalability: string | null
reliability: string | null
security: string | null

## Open Questions
questions:
  - question: string
    impact: enum[high, low]
    recommendation: string
