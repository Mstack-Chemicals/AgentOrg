"""Tests for agentorg.validator."""

import os
import pytest

from agentorg.validator import validate_objective, parse_objective


VALID_OBJECTIVE = """\
## Goal
Build a REST API that serves weather data from a PostgreSQL database.

## Constraints
- Python 3.11 only
- Must use existing PostgreSQL database

## Out of Scope
- No frontend or UI of any kind
- No production deployment

## Budget Cap
100000

## Notes
The database schema already exists.
"""

VALID_OBJECTIVE_NO_BUDGET = """\
## Goal
Build a REST API that serves weather data.

## Constraints
- Python 3.11 only

## Out of Scope
- No frontend
"""

VALID_WITH_CRITERIA = """\
## Goal
Build a CLI tool for managing tasks.

## Constraints
- Python 3.10+

## Out of Scope
- No GUI

## Success Criteria

### Research Phase
- PRDs cover all CLI commands

### Engineering Phase
- All commands pass integration tests

### DevOps Phase
- CI pipeline runs on every push
"""


@pytest.fixture
def tmp_objective(tmp_path):
    """Helper to write an objective.md in a temp dir and return its path."""
    def _write(content: str) -> str:
        path = str(tmp_path / "objective.md")
        with open(path, "w") as f:
            f.write(content)
        return path
    return _write


class TestValidateObjective:
    def test_valid_objective_passes(self, tmp_objective):
        path = tmp_objective(VALID_OBJECTIVE)
        errors = validate_objective(path)
        assert errors == []

    def test_valid_without_budget(self, tmp_objective):
        path = tmp_objective(VALID_OBJECTIVE_NO_BUDGET)
        errors = validate_objective(path)
        assert errors == []

    def test_valid_without_success_criteria(self, tmp_objective):
        path = tmp_objective(VALID_OBJECTIVE_NO_BUDGET)
        errors = validate_objective(path)
        assert errors == []

    def test_missing_file(self, tmp_path):
        path = str(tmp_path / "nonexistent.md")
        errors = validate_objective(path)
        assert len(errors) == 1
        assert "not found" in errors[0]

    def test_missing_goal(self, tmp_objective):
        content = """\
## Constraints
- Python 3.11

## Out of Scope
- No frontend
"""
        errors = validate_objective(tmp_objective(content))
        assert len(errors) == 1
        assert "Goal is missing" in errors[0]

    def test_empty_goal(self, tmp_objective):
        content = """\
## Goal

## Constraints
- Python 3.11

## Out of Scope
- No frontend
"""
        errors = validate_objective(tmp_objective(content))
        assert len(errors) == 1
        assert "Goal is missing" in errors[0]

    def test_goal_with_comments_only(self, tmp_objective):
        content = """\
## Goal
# This is a comment
# Another comment

## Constraints
- Python 3.11

## Out of Scope
- No frontend
"""
        errors = validate_objective(tmp_objective(content))
        assert len(errors) == 1
        assert "Goal is missing" in errors[0]

    def test_long_goal_accepted(self, tmp_objective):
        long_goal = (
            "Sentence one. Sentence two. Sentence three. "
            "Sentence four. Sentence five. Sentence six. "
            "Sentence seven. Sentence eight."
        )
        content = f"""\
## Goal
{long_goal}

## Constraints
- Python 3.11

## Out of Scope
- No frontend
"""
        errors = validate_objective(tmp_objective(content))
        assert errors == []

    def test_goal_with_bullets(self, tmp_objective):
        content = """\
## Goal
- Build an API
- Serve weather data

## Constraints
- Python 3.11

## Out of Scope
- No frontend
"""
        errors = validate_objective(tmp_objective(content))
        assert len(errors) == 1
        assert "paragraph" in errors[0]

    def test_missing_constraints(self, tmp_objective):
        content = """\
## Goal
Build an API.

## Out of Scope
- No frontend
"""
        errors = validate_objective(tmp_objective(content))
        assert len(errors) == 1
        assert "Constraints" in errors[0]

    def test_empty_constraints(self, tmp_objective):
        content = """\
## Goal
Build an API.

## Constraints
# just a comment

## Out of Scope
- No frontend
"""
        errors = validate_objective(tmp_objective(content))
        assert len(errors) == 1
        assert "Constraints" in errors[0]

    def test_missing_out_of_scope(self, tmp_objective):
        content = """\
## Goal
Build an API.

## Constraints
- Python 3.11
"""
        errors = validate_objective(tmp_objective(content))
        assert len(errors) == 1
        assert "Out of Scope" in errors[0]

    def test_invalid_budget_cap_string(self, tmp_objective):
        content = """\
## Goal
Build an API.

## Constraints
- Python 3.11

## Out of Scope
- No frontend

## Budget Cap
abc
"""
        errors = validate_objective(tmp_objective(content))
        assert len(errors) == 1
        assert "positive integer" in errors[0]

    def test_invalid_budget_cap_negative(self, tmp_objective):
        content = """\
## Goal
Build an API.

## Constraints
- Python 3.11

## Out of Scope
- No frontend

## Budget Cap
-100
"""
        errors = validate_objective(tmp_objective(content))
        assert len(errors) == 1
        assert "positive integer" in errors[0]

    def test_invalid_budget_cap_zero(self, tmp_objective):
        content = """\
## Goal
Build an API.

## Constraints
- Python 3.11

## Out of Scope
- No frontend

## Budget Cap
0
"""
        errors = validate_objective(tmp_objective(content))
        assert len(errors) == 1
        assert "positive integer" in errors[0]

    def test_heading_with_markers_stripped(self, tmp_objective):
        """Headings like '## Goal  [REQUIRED]' should be normalised."""
        content = """\
## Goal                                         [REQUIRED]
Build an API.

## Constraints                                  [REQUIRED]
- Python 3.11

## Out of Scope                                 [REQUIRED]
- No frontend
"""
        errors = validate_objective(tmp_objective(content))
        assert errors == []


class TestParseObjective:
    def test_parse_full_objective(self, tmp_objective):
        path = tmp_objective(VALID_OBJECTIVE)
        data = parse_objective(path)
        assert "weather data" in data["goal"]
        assert len(data["constraints"]) == 2
        assert len(data["out_of_scope"]) == 2
        assert data["budget_cap"] == 100000
        assert data["success_criteria"] is None
        assert data["notes"] is not None

    def test_parse_with_criteria(self, tmp_objective):
        path = tmp_objective(VALID_WITH_CRITERIA)
        data = parse_objective(path)
        assert data["success_criteria"] is not None
        assert len(data["success_criteria"]["research"]) == 1
        assert len(data["success_criteria"]["engineering"]) == 1
        assert len(data["success_criteria"]["devops"]) == 1

    def test_parse_no_budget(self, tmp_objective):
        path = tmp_objective(VALID_OBJECTIVE_NO_BUDGET)
        data = parse_objective(path)
        assert data["budget_cap"] is None
        assert data["notes"] is None
