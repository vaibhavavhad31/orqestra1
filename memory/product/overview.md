# Requirements: AI Resource Manager

## Core Value
One place for individuals and organisations to see, plan, allocate and share AI usage capacity (measured in platform **credits**) so that work isn't interrupted when someone runs out. It tracks obligations and allocations only. It never moves real provider credits or bypasses provider limits.

## Personas & Roles
Each account belongs to exactly ONE mode: Individual or Organisation (no toggle).
- **Individual user** (Individual mode): manages personal usage, lends to and borrows from friends, plans personal sessions, hands over tasks.
- **Organisation Admin** (Org mode): manages the org, users, departments, permissions, budgets and expenditure.
- **Manager** (Org mode): monitors team usage, manages allocations, reviews resource requests and handovers, views team reports and session plans.
- **Employee** (Org mode): views personal usage, requests more resources, takes part in handovers, uses the session planner.

RBAC is enforced on the backend. Navigation shows only what the role/mode is allowed to see.
Demo: one-click demo logins for all 4 roles on the login page, plus an in-app "View as role" switcher that switches between the demo accounts. It is available only to demo accounts.

## Features
| id | feature | persona | phase |
|---|---|---|---|
| F-1 | Auth: email/password (JWT, bcrypt) + Emergent-managed Google sign-in; signup chooses Individual or Organisation mode | all | 1 |
| F-2 | Demo logins for 4 roles on the login page + in-app "View as role" switcher | evaluator | 1 |
| F-3 | Design system: tokens, reusable components (cards, tables, badges, charts, empty/loading/error states), Lucide icons | all | 1 |
| F-4 | App shell: sidebar with 11 modules (Overview, AI Usage, Resource Allocation, Credit Lending, Task Handover, Session Planner, Notifications, Reports, Team, Integrations, Settings), top bar, responsive mobile nav | all | 1 |
| F-5 | Mode + role-based navigation and backend permission enforcement | all | 1 |
| F-6 | Database foundation: users, orgs, departments, providers (pluggable registry), usage records, budgets/allocations, lending ledger, resource requests, handovers, sessions, notifications, audit log | system | 1 |
| F-7 | Nexora Technologies seed: ~12 employees across Product/Engineering/Marketing/Operations, plus individual users and friends; providers ChatGPT, Claude, Gemini, Copilot, Perplexity; all marked SIMULATED | evaluator | 1 |
| F-8 | Overview dashboard per mode/role with real DB-driven summary cards and charts | all | 1 |
| F-9 | AI Usage view (read-only): usage by provider/time, "Simulated data" labels | all | 1 |
| F-10 | Placeholder pages for the remaining modules, with polished "coming next" empty states | all | 1 |
| F-11 | Credit Lending ledger: request from friend, lend, accept/decline, outstanding balances, record repayment; disclaimer that no provider credits move | Individual | 2 |
| F-12 | Resource Allocation: org budget, department/employee allocations, underutilised detection, reallocation; employee resource requests with manager approve/reject | Admin, Manager, Employee | 2 |
| F-13 | Task Handover: task-specific context, completed work, pending work, documents (object storage); status flow; no exposure of full AI chat history | all | 3 |
| F-14 | Session Planner: personal sessions (individual/employee) + team view and coordination (manager) | all | 3 |
| F-15 | Notifications: in-app, triggered by lending, requests, handovers and sessions | all | 4 |
| F-16 | Reports & analytics: usage, expenditure in credits, utilisation, CSV export | Admin, Manager, Individual | 4 |
| F-17 | Team management: invite/edit users, roles, departments (Admin); team view (Manager) | Admin, Manager | 4 |
| F-18 | Integrations page: provider registry (all "Simulated / not connected"), extensible structure | all | 4 |
| F-19 | Settings: profile, org settings (Admin), preferences | all | 4 |

## Phases
- **Phase 1: Foundation.** Architecture, DB, auth, design system, shell, mode/role navigation, seed data, Overview + AI Usage (read-only), placeholders elsewhere → F-1..F-10. [phase1/requirement.md](phase1/requirement.md), [phase1/journeys.md](phase1/journeys.md)
- **Phase 2: Lending & Allocation.** Delivers F-11 and F-12.
- **Phase 3: Handover & Session Planner.** Delivers F-13 and F-14.
- **Phase 4: Notifications, Reports, Team, Integrations, Settings.** Delivers F-15..F-19.

## UI/UX Rules
- Premium SaaS look inspired by Linear, Stripe and Notion (not copied). Light theme by default, warm white / very light grey background, deep navy/charcoal text, muted indigo accent.
- Subtle borders and shadows, restrained corner radius, strong spacing and hierarchy. No heavy gradients, no unnecessary animation, no crowded dashboards, no generic AI landing-page look.
- Lucide icons only. Every data view has an empty, a loading (skeleton) and an error state.
- Desktop-first. Fully responsive for tablet and mobile. Individual features must work well on mobile.
- Every simulated figure carries a visible "Simulated" badge or label.

## Integrations
- Auth: custom JWT email/password + Emergent-managed Google Auth.
- Database: MongoDB (Emergent stack: FastAPI + React + MongoDB).
- Object storage (Emergent) for handover documents, from phase 3.
- No AI provider APIs. All provider data is simulated. The provider registry is pluggable for future real connectors.

## Edge Cases
- Lending must never claim real credit transfer. The ledger is obligation tracking only.
- Users cannot lend more than their available balance. A loan cannot be repaid beyond what is outstanding.
- An Individual-mode account cannot reach org endpoints, and vice versa (backend 403).
- An Employee cannot see other employees' detailed usage. A Manager sees only their own department/team.
- A Google sign-in for a new user must choose a mode on first login.

## Seed Data
- Org "Nexora Technologies" with departments Product, Engineering, Marketing and Operations, and ~12 employees (1 Admin, managers, employees) with realistic names and titles.
- Monthly org credit budget, department and employee allocations (some underutilised, some near their limit).
- ~90 days of simulated usage records across ChatGPT, Claude, Gemini, Copilot and Perplexity.
- Individual users (the demo individual plus 3–4 friends) with personal credits and sample lending ledger entries.
- Demo accounts: admin, manager, employee, individual (credentials in /app/memory/test_credentials.md).
