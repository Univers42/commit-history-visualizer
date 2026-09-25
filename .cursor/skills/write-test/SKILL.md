---
name: write-test
description: >-
  Generates tests for existing code in the project's detected test framework
  and idiom. Use when the user asks to write tests, add test coverage, or says
  this needs tests.
---

# Write Tests

## Pack root

Resolve the pack root before any path below. It is `.claude` when
`.claude/tools/facts.sh` exists (this pack installed into a project). Otherwise
it is the repository root (this repo opened directly).

## 0. Detect the framework

- Run `tools/facts.sh` from the pack root — it reports the detected test framework. Write in
  THAT framework, in its idiom (see `rules/test-frameworks.md` in the pack root). Don't introduce a
  second framework; don't hand-roll asserts/mocks it already ships.
- None configured? Pick the canonical default for the stack and say why in one line.

## 1. Read the source

- Understand every public function's contract
- Identify edge cases from the implementation (not just happy path)

## 2. Design test cases (before writing any code)

For each function, list:

- Happy path (normal input → expected output)
- Boundary (empty, zero, max, nil/null)
- Error path (invalid input, resource failure)
- Concurrency (if the function touches shared state)

Present the test plan. Wait for approval.

## 3. Write

- Table-driven / parameterized tests in the detected framework's idiom (Go subtests, `rstest`, `it.each`, `pytest.mark.parametrize`)
- Property-based tests for anything parsing external input (Hypothesis, proptest, fast-check, `testing/quick`)
- One test function per behavior, not per source function
- Test names describe the scenario: `test_login_rejects_expired_token`
- No test depends on another test's state
- No sleep() — use channels, signals, or mocks

## 4. Verify

- All new tests pass
- All existing tests still pass
- No flaky tests (run 3 times)
- Report coverage delta

## 5. Report

- Framework used, and the one-line reason if none was configured
- New tests (names) and the command whose output shows they pass
- Existing suite still passes (command + result)
- Flake check: three runs, all green
- Coverage delta, or that the project has no coverage command
