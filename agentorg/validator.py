"""Validate and parse objective.md against the agentorg schema."""

from __future__ import annotations

import os
import re


def _parse_sections(text: str) -> dict[str, str]:
    """Split markdown text by ## headings into {normalised_name: content}."""
    sections: dict[str, str] = {}
    parts = re.split(r"^## ", text, flags=re.MULTILINE)
    for part in parts[1:]:  # skip preamble before first ##
        lines = part.split("\n", 1)
        raw_heading = lines[0].strip()
        content = lines[1] if len(lines) > 1 else ""
        # Normalise: lowercase, strip trailing markers like [REQUIRED]
        name = re.sub(r"\s*\[.*?\]\s*$", "", raw_heading).strip().lower()
        sections[name] = content
    return sections


def _strip_comments(text: str) -> str:
    """Remove lines that are template comments (# not ##)."""
    lines = []
    for line in text.split("\n"):
        stripped = line.lstrip()
        if stripped.startswith("# ") and not stripped.startswith("## "):
            continue
        if stripped == "#":
            continue
        lines.append(line)
    return "\n".join(lines)


def _extract_bullet_items(text: str) -> list[str]:
    """Extract non-empty bullet items (- item) from text."""
    items = []
    for line in text.split("\n"):
        match = re.match(r"^\s*-\s+(.+)", line)
        if match:
            item = match.group(1).strip()
            if item:
                items.append(item)
    return items


def _count_sentences(text: str) -> int:
    """Count sentences in a paragraph. Simple heuristic: split on sentence-ending punctuation."""
    text = text.strip()
    if not text:
        return 0
    # Split on sentence-ending punctuation followed by whitespace or end-of-string
    sentences = re.split(r"(?<=[.!?])\s+", text)
    # Filter out empty strings
    sentences = [s for s in sentences if s.strip()]
    # If the text doesn't end with punctuation, the last chunk is still a sentence
    return max(len(sentences), 1) if text else 0


def validate_objective(path: str = "objective.md") -> list[str]:
    """Validate objective.md. Returns list of error strings; empty list means valid."""
    errors: list[str] = []

    if not os.path.exists(path):
        return ["objective.md not found\n    Run agentorg init to create it."]

    with open(path, "r") as f:
        text = f.read()

    sections = _parse_sections(text)

    # --- Goal ---
    goal_raw = sections.get("goal", "")
    goal_content = _strip_comments(goal_raw).strip()

    if not goal_content:
        errors.append(
            "Goal is missing\n    Add a goal paragraph to objective.md and re-run."
        )
        return errors

    # Check for bullet points in goal
    if re.search(r"^\s*-\s+", goal_content, re.MULTILINE):
        errors.append(
            "Goal must be a paragraph, not a bullet list\n"
            "    Rewrite the goal as a paragraph in objective.md and re-run."
        )
        return errors

    # --- Constraints ---
    constraints_raw = sections.get("constraints", "")
    constraints_content = _strip_comments(constraints_raw)
    constraints_items = _extract_bullet_items(constraints_content)

    if not constraints_items:
        errors.append(
            "Constraints section is missing\n"
            "    Add at least one constraint to objective.md and re-run."
        )
        return errors

    # --- Out of Scope ---
    oos_raw = sections.get("out of scope", "")
    oos_content = _strip_comments(oos_raw)
    oos_items = _extract_bullet_items(oos_content)

    if not oos_items:
        errors.append(
            "Out of Scope section is missing\n"
            "    Add at least one out-of-scope item to objective.md and re-run."
        )
        return errors

    # --- Code Root ---
    code_root_raw = sections.get("code root", "")
    code_root_content = _strip_comments(code_root_raw).strip()

    if code_root_content:
        if not os.path.isdir(code_root_content):
            errors.append(
                f"Code root path '{code_root_content}' does not exist\n"
                "    Fix the code root in objective.md and re-run."
            )
            return errors

    # --- Budget Cap ---
    budget_raw = sections.get("budget cap", "")
    budget_content = _strip_comments(budget_raw).strip()

    if budget_content:
        try:
            budget_val = int(budget_content)
            if budget_val <= 0:
                raise ValueError
        except (ValueError, TypeError):
            errors.append(
                "Budget cap must be a positive integer\n"
                "    Fix the budget cap in objective.md and re-run."
            )
            return errors

    return errors


def _parse_success_criteria(text: str) -> dict[str, list[str]] | None:
    """Parse the Success Criteria section into per-phase lists."""
    content = _strip_comments(text)
    if not content.strip():
        return None

    criteria: dict[str, list[str]] = {
        "research": [],
        "engineering": [],
        "devops": [],
    }

    # Split by ### sub-headings
    sub_parts = re.split(r"^### ", content, flags=re.MULTILINE)
    for part in sub_parts[1:]:
        lines = part.split("\n", 1)
        sub_heading = lines[0].strip().lower()
        sub_content = lines[1] if len(lines) > 1 else ""

        if "research" in sub_heading:
            criteria["research"] = _extract_bullet_items(sub_content)
        elif "engineering" in sub_heading:
            criteria["engineering"] = _extract_bullet_items(sub_content)
        elif "devops" in sub_heading:
            criteria["devops"] = _extract_bullet_items(sub_content)

    # If all empty, treat as absent
    if not any(criteria.values()):
        return None

    return criteria


def parse_objective(path: str = "objective.md") -> dict:
    """Parse objective.md into structured dict. Call after validation passes.

    Returns:
        {
            "goal": str,
            "constraints": [str],
            "out_of_scope": [str],
            "budget_cap": int | None,
            "success_criteria": {"research": [...], "engineering": [...], "devops": [...]} | None,
            "notes": str | None,
        }
    """
    with open(path, "r") as f:
        text = f.read()

    sections = _parse_sections(text)

    # Goal
    goal = _strip_comments(sections.get("goal", "")).strip()

    # Constraints
    constraints = _extract_bullet_items(
        _strip_comments(sections.get("constraints", ""))
    )

    # Out of Scope
    out_of_scope = _extract_bullet_items(
        _strip_comments(sections.get("out of scope", ""))
    )

    # Budget Cap
    budget_raw = _strip_comments(sections.get("budget cap", "")).strip()
    budget_cap = int(budget_raw) if budget_raw else None

    # Success Criteria
    success_criteria = _parse_success_criteria(
        sections.get("success criteria", "")
    )

    # Code Root
    code_root_raw = _strip_comments(sections.get("code root", "")).strip()
    code_root = code_root_raw if code_root_raw else None

    # Notes
    notes_raw = _strip_comments(sections.get("notes", "")).strip()
    notes = notes_raw if notes_raw else None

    return {
        "goal": goal,
        "constraints": constraints,
        "out_of_scope": out_of_scope,
        "budget_cap": budget_cap,
        "success_criteria": success_criteria,
        "code_root": code_root,
        "notes": notes,
    }
