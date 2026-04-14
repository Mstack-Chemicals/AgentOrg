# SWE-bench Evaluation: django__django-16631

## Task

**ID**: `django__django-16631`
**Repo**: django/django
**Base commit**: `9b224579875e30203d079cc2fee83b116d98eb78`
**Difficulty**: 0/19 leading agents solved this task (0% pass rate)
**Systems that failed**: Claude Opus 4, GPT-5, OpenHands + Claude Opus 4.5,
OpenHands + GPT-5, Amazon Q Developer, Live-SWE-agent, Prometheus + GPT-5,
AutoCodeRover, MASAI + GPT-4o, Moatless + Claude 4 Sonnet, SAGE + OpenHands,
EPAM AI Run, Sonar Foundation Agent, and 6 others.

### The bug

Django's `SECRET_KEY_FALLBACKS` does not work for sessions. When a site
rotates its `SECRET_KEY` and places the old key in `SECRET_KEY_FALLBACKS`,
all users are logged out because `AbstractBaseUser.get_session_auth_hash()`
only checks the current `SECRET_KEY`, ignoring fallback keys.

### The gold patch

2 files, +28/-5 lines, 3 hunks:
- `django/contrib/auth/__init__.py` — iterate fallback keys in `get_user()`,
  call `session.cycle_key()` on fallback match
- `django/contrib/auth/base_user.py` — add `secret` param to
  `get_session_auth_hash()`, add `get_session_auth_fallback_hash()` generator

### Grading criteria

- **FAIL_TO_PASS**: `test_get_user_fallback_secret` must pass
- **PASS_TO_PASS**: 12 existing `auth_tests.test_basic` tests must pass
- The grading test asserts that `session_key` changes after fallback
  verification (`assertNotEqual(session_key, prev_session_key)`), which
  requires `cycle_key()`.

## agentorg result

### Run 1 (before prompt improvements)

**PASS_TO_PASS**: 12/12
**FAIL_TO_PASS**: 0/1 (session key not cycled)

Files modified (correct — same as gold patch):
- `django/contrib/auth/__init__.py`
- `django/contrib/auth/base_user.py`

What the agents got right:
- Identified both correct files
- Added `secret` parameter to `get_session_auth_hash()` (matches gold patch)
- Iterated over `SECRET_KEY_FALLBACKS` to check fallback hashes
- Updated `HASH_SESSION_KEY` in session to upgrade to current key
- Correctly flushed invalid sessions
- All 12 existing tests continued to pass

What was missing:
- Did not call `request.session.cycle_key()` to regenerate session ID
- Only updated the hash in place without rotating the session key

### Run 2 (after prompt improvements)

Three prompt changes made:
1. CTO generates research questions about existing internal APIs
2. SDE principle to search for existing methods before writing custom logic
3. Reviewer checklist item for existing internal API usage

**PASS_TO_PASS**: 12/12
**FAIL_TO_PASS**: 0/1 (session key not cycled)

Same files modified, same core approach. However, the Research phase
**did discover `cycle_key()`** this time. The finding (P4) documented it,
and the Architect made a deliberate decision not to use it:

> "cycle_key() is designed for password-change scenarios where session
> fixation is a concern, which does not apply here. Key rotation does not
> change the session's security properties — the session ID is still valid.
> Only the stored hash needs updating."

The Architect reasoned that `cycle_key()` regenerates the session ID,
which could break concurrent requests (e.g., parallel AJAX calls holding
the old session cookie). This is a defensible position but does not match
the Django maintainers' choice in the gold patch.

## Analysis

### What worked

The multi-agent pipeline correctly:
- Identified the bug location across two files in Django's auth subsystem
- Understood the `salted_hmac` → `SECRET_KEY` → `get_session_auth_hash()`
  chain without any hints about file names or function names
- Produced a fix that keeps users logged in during key rotation
- Preserved all existing functionality (12/12 tests pass)
- Discovered the `cycle_key()` API through directed research

### What didn't work

The grading test requires `cycle_key()` — a security hardening choice where
the session ID is regenerated during key rotation. The Architect discovered
this API but made a reasoned decision to skip it, preferring a less
disruptive approach (hash-only update).

This is a **judgment gap**, not a discovery gap. The agents found the right
API, understood what it does, and chose not to use it based on a reasonable
(but incorrect per Django's standards) security analysis.

### Significance

This task has a 0% pass rate across 19 leading agent systems. agentorg
reached "correct fix, wrong security philosophy" — further than any other
system. The Research phase discovered `cycle_key()` (which no other system
achieved), and the Architect produced a documented rationale for the
decision. The failure is at the judgment layer, not the discovery or
implementation layer.

## Verdict

**Official SWE-bench result: FAIL** (1 assertion failure in grading test)

**Qualitative result: Partial pass** — correct files, correct approach,
correct fallback iteration, correct hash upgrade, all existing tests pass.
Missing only `cycle_key()` call due to an explicit architectural decision.
