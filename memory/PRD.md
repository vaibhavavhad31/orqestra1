# AI Resource Manager — PRD

## Original problem statement
Build Phase 1 (Foundation) of "AI Resource Manager", a premium responsive SaaS app (FastAPI + React + MongoDB). Specs: /app/memory/product/overview.md, phase1/requirement.md, phase1/journeys.md (acceptance criteria JRN-1..18). Scope: F-1..F-10. Auth: JWT + Emergent Google, one mode per account, 4 demo logins, a demo-only View as role switcher, backend RBAC, a provider registry in the DB, simulated usage in credits, an idempotent Nexora seed, Overview + AI Usage with a 7/30/90 filter, and placeholders for everything else.

## Personas
Individual, Organisation Admin, Manager, Employee (plus the evaluator, via demo accounts).

## Architecture
- Backend: /app/backend/{core (config, db, security, permissions, deps, indexes), models/schemas.py, services (users, validation, usage, overview, seed), routers (auth, demo, dashboard, org)}. OpenAPI at /api/openapi.json, docs at /api/docs.
- Frontend: lib (api, modules, format), context/AuthContext, hooks/useApi, components (common, charts, shell, auth, overview, usage), pages.
- The RBAC module matrix lives in core/permissions.py. /auth/me returns allowed_modules, which drives the nav and the route guards.

## Implemented (2026-11-21)
- JWT auth with httpOnly cookies, refresh, brute-force lockout and inline signup field errors. Google auth with a mode picker on first login.
- Demo login for 4 roles. /api/demo/switch requires both the current user and the target to be demo accounts, otherwise 403.
- App shell: sidebar, topbar, mobile drawer under 768px, role-based nav, access-denied state, polished placeholders.
- Seed: Nexora (12 people, 4 departments, 50,000 credits/month budget), 4 individuals, 5 providers (all simulated), 90 days of usage (~4,958 records), lending ledger, sample requests, handovers, sessions and notifications.
- Overview (one view per role) and AI Usage (role-scoped, 7/30/90 days, Simulated badge, loading/empty/error states).
- Tested: 29/29 backend tests and all journeys JRN-1..18 pass.

## Phase 1 review fixes (2026-11-21)
- Credit Lending is a read-only page for Individuals: summary, ledger and disclaimer. Actions are disabled and marked "Coming in Phase 2".
- AI Usage gained a provider filter, department/member filters for Admin and Manager (scoped on the server, 403 outside scope), comparison with the previous period, and weekly buckets for 90 days.
- Overview and AI Usage share one calculation (services/usage.scoped_usage). Reconciliation is verified by backend/scripts/reconcile.py.
- Pages remount on a View-as switch, so no data from the previous role survives. Individual mode never shows org data.
- Mobile tap targets and aria-labels improved, and charts no longer overflow on resize (min-w-0).
- Tested: 44/44 backend tests and all requested flows pass (iteration_2).

## Phase 2: Credit Lending & Resource Allocation (2026-11-21)
- Friends: request by email, accept or decline. "No individual user found with that email" for unknown or org emails.
- Lending: request or offer → pending → active | declined | cancelled. Repayments are recorded by the borrower, then confirmed or disputed by the lender, and partial repayment is allowed. Due date → Overdue. Entry sheet with a history timeline. Available = capacity − 30d usage − lent + borrowed. The disclaimer "Obligation tracking only. No provider credits are transferred." is on every lending screen.
- Allocation: Admin edits org and department budgets. Admin/Manager edit member allocations, reallocate, and approve (partial allowed) or reject requests. Employees request and cancel. Exact REQ error copy. Underutilised panel with suggestions.
- Integrity: conditional updates return 409 on double actions. Per-lender, per-department and per-org locks (core/locks.py) stop races across different entries or requests. Audit and notification records are written for every action. reconcile.py also checks allocation sums and lending balances.
- Seed: Tomás, Hana and Kwame are now demo accounts (password Demo@12345) and appear in the View-as "Individual friends" group. Seeded friendships, a v2 ledger with history, and repayments (including one awaiting confirmation and one overdue loan).
- Tested: iteration_3 passed 21/21 for Phase 2 plus the Phase 1 regression. After the race fix: race probe 3/3 correct, 65/65 pytest, reconcile ALL OK.

## Phase 3: Task Handover & Session Planner (2026-11-21)
- Handovers: create/edit (creator, while pending), accept/reject(reason)/complete/cancel, 403 wrong actor, 409 invalid transition, atomic status-conditional updates, timeline, privacy copy, scoped assignees (org colleagues / accepted friends), Received/Sent/All tabs (All = Manager dept, Admin org).
- Attachments via Emergent Object Storage (PDF/PNG/JPG/DOCX/TXT/MD, ≤10 MB, ≤5 per task), DB refs with is_deleted, download only via authorised backend endpoint.
- Planner: personal sessions (UTC stored, local displayed), validation, overlap warning, edit/cancel/complete, reminders 15/30/60 via 60s asyncio loop with atomic reminder_sent (once only), provider reset times "Entered by you", Team view (Manager dept / Admin org) with member filter, suggest new time → owner accept/dismiss, 7-column week grid on desktop and day list at <768px.
- Seed additions: hnd_002..005, ses_101..108 (next week). Legacy hnd_001/ses_001/ses_002 read through a normaliser, not rewritten.

## Phase 4: Notifications, Reports, Team, Integrations, Settings (2026-11-21)
- Notifications: bell with unread count (30s poll + instant refresh on read), latest-8 dropdown, page with All/Unread, Pending actions, deep links (?open= for lending/handover), owner-only (403).
- Reports: Usage (provider/department/member/daily) + Allocation (Admin/Manager) or Lending summary (Individual), 7/30/90, CSV via csv module + StreamingResponse, "Simulated data" label, built on the same overview/usage services (totals verified equal for 4 roles x 3 ranges). Employee 403.
- Team: Admin search/filter, add member with one-time temp password, edit role/department/title, deactivate/reactivate (login blocked "Your account has been deactivated"), self/demo protection, departments create/rename. Manager read-only own dept; others 403.
- Integrations: 5 providers "Simulated, not connected", per-user (Individual) / per-org (Admin) simulated toggle persisted in integration_states.
- Settings: profile, change password (demo blocked with exact copy, Google-only notice), notification prefs per category enforced in notify(), org rename (Admin).
- Seed additions: none.

## Security follow-up (2026-11-21)
- Server-side sessions (auth_sessions, TTL): every token carries a session id; logout revokes it (copied tokens get 401); deactivation revokes all of a user's sessions; demo logins and View-as each get their own session.
- First-login password: admin-created users (must_change_password) get 403 "Password change required" on all APIs except auth/me, logout and /auth/set-password; the frontend shows a "Set your new password" screen until it's set.

## Backlog
