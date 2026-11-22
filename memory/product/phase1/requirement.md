# Phase 1: Foundation (phase-1)

## Goal
A stable, polished, authenticated application shell with mode- and role-aware navigation, a complete database foundation, Nexora seed data, and working Overview and AI Usage pages. All other modules are polished placeholders. See ../overview.md for personas, UI rules and seed data.

## Functional requirements
- REQ-1 [always] The system shall offer email/password signup and login using hashed passwords and JWT sessions.
- REQ-2 [unwanted] If login credentials are wrong, then the system shall show "Invalid email or password".
- REQ-3 [always] The system shall offer "Continue with Google" via Emergent-managed Google Auth.
- REQ-4 [event] When a new user signs up (email or Google first login), the system shall require a choice of "Individual" or "Organisation" mode.
- REQ-5 [unwanted] If signup data is invalid (bad email, password under 8 chars, duplicate email), then the system shall show an inline field error.
- REQ-6 [always] The login page shall show four one-click demo logins: Organisation Admin, Manager, Employee, Individual.
- REQ-7 [state] While signed in as a demo account, the system shall show a "View as role" switcher that switches to another demo account's session.
- REQ-8 [always] The sidebar shall list only the modules allowed for the current mode and role, in this order: Overview, AI Usage, Resource Allocation, Credit Lending, Task Handover, Session Planner, Notifications, Reports, Team, Integrations, Settings.
- REQ-9 [always] Individual mode shall show: Overview, AI Usage, Credit Lending, Task Handover, Session Planner, Notifications, Reports, Integrations, Settings (no Resource Allocation, no Team). (interpreted)
- REQ-10 [always] Organisation Admin shall see all 11 modules except Credit Lending. (interpreted)
- REQ-11 [always] Manager shall see all modules except Credit Lending and Integrations. (interpreted)
- REQ-12 [always] Employee shall see Overview, AI Usage, Resource Allocation (own allocation and requests), Task Handover, Session Planner, Notifications, Settings. (interpreted)
- REQ-13 [unwanted] If a user calls an API or opens a route outside their mode or role, then the system shall return 403 (API) or show a "You don't have access to this page" state (UI).
- REQ-14 [always] The backend shall persist all entities listed in F-6 in MongoDB, with a provider registry collection that adds providers through data, not code changes.
- REQ-15 [always] The seed shall create Nexora Technologies with ~12 employees across Product, Engineering, Marketing and Operations, plus individual users, ~90 days of usage across ChatGPT, Claude, Gemini, Copilot and Perplexity, budgets/allocations and sample lending entries.
- REQ-16 [always] The Overview page shall show DB-driven summary cards and at least one chart tailored to the role (Admin: org budget used/remaining and spend by department; Manager: team usage; Employee and Individual: personal credits used/remaining).
- REQ-17 [always] The AI Usage page shall show usage over time and by provider, scoped to the role (Admin: org; Manager: department; Employee and Individual: self), with a date range filter (7/30/90 days).
- REQ-18 [always] Every view displaying provider usage shall show a visible "Simulated data" label.
- REQ-19 [always] Non-built modules shall render a polished placeholder with the module name, a one-line purpose and "Coming in a later phase".
- REQ-20 [always] Each data view shall have a loading skeleton, an empty state and an error state.
- REQ-21 [always] The layout shall adapt from a sidebar on desktop to a collapsible drawer on mobile (<768px).
- REQ-22 [event] When the user clicks Log out, the system shall end the session and return to the login page.
- REQ-23 [always] The backend shall expose its OpenAPI spec at /api/openapi.json.

## Quality requirements
Q-1  Tag: Security.RBAC
     Scale: % of cross-role/cross-mode API calls correctly rejected with 403
     Meter: tester curls each protected endpoint with every demo role
     Must: 100%
     Plan: 100%
Q-2  Tag: Performance.PageLoad
     Scale: ms from navigation to Overview data rendered
     Meter: browser timing, 3 trials
     Must: 2500
     Plan: 1200
Q-3  Tag: Usability.Responsive
     Scale: number of layout breakages (overflow, overlapping, clipped text) at 390px, 768px, 1440px
     Meter: screenshots of all routes
     Must: 0 on Overview, AI Usage and login
     Plan: 0 everywhere
Q-4  Tag: Trust.SimulatedLabel
     Scale: % of usage views missing the "Simulated" label
     Meter: tester visual check
     Must: 0%
     Plan: 0%
Q-5  Tag: Data.Persistence
     Scale: seed data surviving a backend restart (idempotent seed, no duplicates)
     Meter: restart backend, count users
     Must: same count
     Plan: same count
Q-6  Tag: Cosmetic.Polish
     Scale: premium-SaaS look per UI rules (no gradients overload, consistent spacing, Lucide icons)
     Meter: human
     Must: evaluator judges "real product", not template
     Plan: same
