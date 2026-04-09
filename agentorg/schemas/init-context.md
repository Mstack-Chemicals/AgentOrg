# init-context.md — Schema

## Objective
goal: string
constraints: string[]
out_of_scope: string[]
success_criteria:
  research: string[]
  engineering: string[]
  devops: string[]

## Environment
os: string
shell: string
language_runtimes: string[]
package_managers: string[]
git_config:
  user: string
  default_branch: string
available_tools: string[]

## Project State
is_greenfield: bool
existing_structure: string
detected_stack: string[]

## Run Metadata
initiated_at: string
budget_cap: int | null
