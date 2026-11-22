# Phase 4: Notifications, Reports, Team, Integrations, Settings (phase-4)

## Goal
Complete the MVP with the supporting modules, reusing the existing collections, components and RBAC. No placeholders remain. Phases 1–3 and the seeded data must be preserved. See ../overview.md (F-15..F-19). Credit-lean: the simplest reliable implementation.

## Functional requirements

### Notifications (all roles)
- REQ-87 [always] The top bar shall show a bell with an unread count, refreshed every 30 seconds, from the existing notifications collection.
- REQ-88 [always] The bell dropdown shall show the latest 8 notifications; the Notifications page shall list all of them with an All / Unread filter, each linking to its related item (loan, request, handover, session).
- REQ-89 [event] When the user marks one notification as read (or clicks "Mark all as read"), the system shall update the unread count immediately.
- REQ-90 [always] Users shall only see their own notifications (403 on others).
- REQ-91 [always] The Notifications page shall show a "Pending actions" section counting items awaiting the user (lending to accept or confirm, requests to approve, handovers to accept, time suggestions) (interpreted).

### Reports (Admin, Manager, Individual)
- REQ-92 [always] Reports shall offer a Usage report (by provider, by member/department within scope, daily totals) and an Allocation report (budget, allocated, used, remaining, utilisation, status), with a 7/30/90-day range filter; the Individual's Allocation report is replaced by a Lending summary (interpreted).
- REQ-93 [event] When the user clicks "Export CSV", the system shall download a CSV of the shown report, with headers, scoped to the user's role.
- REQ-94 [always] Report totals shall match Overview and AI Usage for the same range and scope.
- REQ-95 [always] Reports and CSVs shall be labelled "Simulated data".
- REQ-96 [unwanted] If an Employee calls the reports API, then the system shall return 403.

### Team (Admin manages; Manager read-only)
- REQ-97 [always] The Admin shall see all org members with name, email, role, department, status and allocation, with search and a department filter.
- REQ-98 [event] When the Admin adds a user (name, email, role, department, title), the system shall create the account and show a one-time temporary password on screen.
- REQ-99 [unwanted] If the email already exists or a field is missing, then the system shall show an inline error.
- REQ-100 [event] When the Admin edits a user's role, department or title, the system shall save it and the user's navigation shall follow the new role on next load.
- REQ-101 [event] When the Admin deactivates a user, the system shall block that user's login with "Your account has been deactivated".
- REQ-102 [unwanted] If the Admin tries to deactivate or demote themselves, or a demo account, then the system shall reject it with a clear message (interpreted).
- REQ-103 [always] The Admin shall create and rename departments.
- REQ-104 [always] A Manager shall see their own department members read-only.

### Integrations (all roles)
- REQ-105 [always] The Integrations page shall list ChatGPT, Claude, Gemini, Copilot and Perplexity from the provider registry, each with status "Simulated, not connected".
- REQ-106 [event] When a user toggles "Simulated connection", the system shall persist the per-user (Individual) or per-org (Admin) state and show "Simulated connection active", with the note "No real provider data is retrieved."
- REQ-107 [always] For Managers, Integrations shall stay hidden (per REQ-11), and Employees shall not see it.

### Settings (all roles)
- REQ-108 [always] Users shall edit their profile name and job title.
- REQ-109 [event] When a user changes their password (current, new ≥ 8 chars, confirm), the system shall save it.
- REQ-110 [unwanted] If the current password is wrong or the new ones mismatch, then the system shall show an inline error.
- REQ-111 [state] While the account is a demo account, the system shall block password changes with "Password changes are disabled for demo accounts" (interpreted).
- REQ-112 [always] Users shall toggle notification preferences per category (lending, allocation, handover, sessions); disabled categories create no new notifications.
- REQ-113 [always] The Admin shall edit the organisation name.
- REQ-114 [always] Google-only accounts shall see "Signed in with Google" instead of the password section.
- REQ-115 [always] Every Phase 4 page shall have loading, empty and error states, and be responsive at 390px.

## Quality requirements
Q-17 Tag: Integrity.Reports
     Scale: mismatches between report/CSV totals and Overview/Usage
     Meter: compare API values for 4 roles × 3 ranges
     Must: 0
     Plan: 0
Q-18 Tag: Security.Team
     Scale: % of non-admin team-management calls rejected
     Meter: curl as Manager, Employee and Individual
     Must: 100%
     Plan: 100%
Q-19 Tag: Usability.Mobile
     Scale: Phase 4 pages with horizontal overflow at 390px
     Meter: browser
     Must: 0
     Plan: 0
