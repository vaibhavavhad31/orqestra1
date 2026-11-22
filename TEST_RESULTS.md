# Orqestra test results (22 Nov 2026)

Environment: local build in an isolated workspace. MongoDB 8.3, Python 3.13, Node 22, Chrome (Playwright). No Emergent services.

## Summary

| Suite | Passed | Failed |
| --- | --- | --- |
| Original prototype, before changes (baseline) | 105 | 6 |
| Backend API suite after changes (existing + new) | **131** | **0** |
| Browser walkthrough across all roles | **15** | **0** |
| Production configuration smoke test (prod dependencies only, Secure cookies, SPA served by FastAPI) | pass | — |
| Clean-folder frontend build from `package.json` + `yarn.lock` (mirrors the Docker build stage) | pass | — |

The 6 baseline failures were all caused by Emergent-only dependencies or the test environment: Emergent object storage unreachable (attachments), Emergent Google auth unreachable, Secure-only cookies over local HTTP (2), and the reconcile script expecting `/app/backend` (2). All are resolved.

## Backend API suite, per module

| Module | Passed | Failed |
| --- | --- | --- |
| `e1_tests.test_orqestra_mvp` (**new**: tasks, decomposition, dependencies, allocation, slots, privacy) | 20 | 0 |
| `e1_tests.test_tscheck_auth` | 3 | 0 |
| `e1_tests.test_tscheck_lending` | 2 | 0 |
| `e1_tests.test_tscheck_overview_usage` | 6 | 0 |
| `e1_tests.test_tscheck_p2_allocation` | 4 | 0 |
| `e1_tests.test_tscheck_p2_lending` | 5 | 0 |
| `e1_tests.test_tscheck_p3_handover` (incl. attachment upload/download hash check, now via GridFS) | 4 | 0 |
| `e1_tests.test_tscheck_p3_planner` (incl. reminder sent exactly once) | 4 | 0 |
| `e1_tests.test_tscheck_p4` | 5 | 0 |
| `e1_tests.test_tscheck_rbac` | 6 | 0 |
| `e1_tests.test_tscheck_reconcile_independence` | 2 | 0 |
| `e1_tests.test_tscheck_switch` | 3 | 0 |
| `e1_tests.test_tscheck_usage_filters` | 2 | 0 |
| `tests.test_phase1_api` | 29 | 0 |
| `tests.test_phase1_round2` | 15 | 0 |
| `tests.test_phase2_lending_allocation` | 21 | 0 |

Existing tests changed on purpose (behaviour changed by design):
- `test_allowed_modules`: every role now also has the **Tasks** module.
- `test_fake_session`: Google sign-in returns 503 ("not available on this deployment") unless re-enabled.
- Reconcile tests: run the script from the repository instead of Emergent's fixed `/app/backend` path.

New MVP tests cover: rule-based breakdown per category; parallel waves; dependency loops rejected; invalid estimates rejected; blocked sub-tasks can't start; goal closing requires all sub-tasks done and builds a summary; ranked candidates with reasons; employees see only qualitative capacity for colleagues; no assignment outside the workspace; goals hidden from unrelated users; assignee can update status but not reassign; slot suggestion inside working hours, sized from the estimate, no overlap with booked sessions; owner scheduling becomes a suggestion to the assignee; admin sees handover metadata only; parties see content and can download files, admins can't; duplicate handover within 2 minutes refused; admin cross-department reallocation suggestions; Google sign-in disabled; Tasks module visible to all roles.

## Browser walkthrough (`backend/e2e/ui_walkthrough.py`)

| Step | Result |
| --- | --- |
| Login page shows Orqestra, no Google button | PASS |
| No PostHog / Emergent scripts in the page; `window.posthog` undefined | PASS |
| Manager demo login lands on Overview | PASS |
| Tasks page lists the seeded goal | PASS |
| Manager breaks a goal into sub-tasks and saves it (waves shown) | PASS |
| Manager gets ranked assignees with reasons, assigns, and gets a slot | PASS |
| Starting a sub-task before its dependency is refused | PASS |
| Manager Resource Allocation still loads | PASS |
| Admin sees handover metadata only (content restricted) | PASS |
| Admin sees reallocation suggestions (previously empty) | PASS |
| Admin: every module page loads | PASS |
| Employee sees goals they work on and their planner | PASS |
| Individual: Credit Lending and Tasks load | PASS |
| Tasks page renders on a phone-sized screen | PASS |
| No uncaught JavaScript errors | PASS |

## Not tested here

- **Building the Docker image itself:** Docker Hub is blocked in this workspace. Both stages were reproduced outside Docker (clean `yarn install --frozen-lockfile` + build; Python 3.13 with `requirements-prod.txt` only). The first Render build is the real check.
- **Render and MongoDB Atlas:** they can't be reached from this workspace.
- **The optional LLM decomposition path** with a real key (no key, no network to providers). Its failure fallback to the rules is in the code.
- **Google sign-in** (disabled by design).
