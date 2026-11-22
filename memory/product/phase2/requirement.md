# Phase 2: Credit Lending & Resource Allocation (phase-2)

## Goal
Make peer-to-peer lending (Individual mode) and organisational resource allocation (Organisation mode) fully working, with every action persisted, permission-checked and reconciled with the Phase 1 dashboards. Everything is platform-tracked credits only; no provider credits move. See ../overview.md (F-11, F-12). Phase 1 journeys must keep passing, except where superseded below.

## Functional requirements

### Credit Lending (Individual mode only)
- REQ-24 [always] Each individual shall have a personal monthly credit capacity, with available = capacity − own usage − lent outstanding + borrowed outstanding (interpreted).
- REQ-25 [always] An individual shall manage a Friends list; adding a friend by email of an existing Individual account sends a connection request that the other user accepts or declines (interpreted).
- REQ-26 [unwanted] If the email does not belong to an Individual account, then the system shall show "No individual user found with that email".
- REQ-27 [event] When an individual submits "Request credits" to a friend (amount, reason, optional due date), the system shall create a pending entry visible to both parties.
- REQ-28 [event] When an individual submits "Lend credits" to a friend (amount, note, optional due date), the system shall create a pending offer the friend can accept or decline.
- REQ-29 [unwanted] If the amount is ≤ 0, non-integer, or the target is not a friend, then the system shall reject the action with an inline error.
- REQ-30 [event] When the lender accepts a borrow request (or the borrower accepts a lend offer), the system shall set the entry to "active" and update both users' available credits.
- REQ-31 [unwanted] If accepting would exceed the lender's available credits, then the system shall block it with "Not enough available credits to lend".
- REQ-32 [event] When the counterparty declines, the system shall set the status to "declined" with no balance change.
- REQ-33 [event] When the initiator cancels a pending entry, the system shall set the status to "cancelled".
- REQ-34 [event] When the borrower records a repayment (partial or full), the system shall create a repayment record with status "awaiting confirmation".
- REQ-35 [unwanted] If the repayment exceeds the outstanding amount, then the system shall reject it with "Repayment exceeds outstanding amount".
- REQ-36 [event] When the lender confirms a repayment, the system shall reduce the outstanding amount, and set the loan to "repaid" when it reaches 0.
- REQ-37 [event] When the lender disputes a repayment, the system shall mark it "disputed" with no balance change.
- REQ-38 [state] While a loan is active past its due date, the system shall show an "Overdue" badge.
- REQ-39 [always] The Credit Lending page shall show summary cards (lent outstanding, borrowed outstanding, net position, pending actions), tabs All / Borrowed / Lent / Pending, an entry detail with a full history timeline, and the disclaimer "Obligation tracking only. No provider credits are transferred."
- REQ-40 [always] Only the two parties of a lending entry shall be able to view or act on it (403 otherwise).
- REQ-41 [always] The Individual Overview cards shall reflect the lending changes immediately (supersedes the read-only lending state from the Phase 1 review).

### Resource Allocation (Organisation mode)
- REQ-42 [always] The Admin shall edit the org monthly budget and each department's budget.
- REQ-43 [unwanted] If department budgets would exceed the org budget, then the system shall reject the change with "Department budgets exceed organisation budget".
- REQ-44 [always] The Admin (any department) and Manager (own department) shall set employee allocations.
- REQ-45 [unwanted] If employee allocations would exceed the department budget, then the system shall reject the change with "Allocations exceed department budget".
- REQ-46 [always] The Allocation page shall list members with allocation, used, remaining, utilisation % and a status of Underutilised (<40% of the pro-rated allocation), Healthy, or Near limit (≥85%) (interpreted).
- REQ-47 [always] The page shall show an "Underutilised allocations" panel with suggested reallocations from underutilised members to near-limit members.
- REQ-48 [event] When a Manager or Admin reallocates N credits from member A to member B, the system shall move the allocation and record it in the audit log.
- REQ-49 [unwanted] If N exceeds A's unused allocation, or a Manager targets another department, then the system shall reject the change (400/403).
- REQ-50 [event] When an Employee submits a resource request (amount, reason, urgency low/normal/high), the system shall create a pending request visible to their department Manager and the Admin.
- REQ-51 [unwanted] If the amount is ≤ 0 or the reason is empty, then the system shall show an inline error.
- REQ-52 [event] When a Manager/Admin approves a request (optionally a partial amount), the system shall increase the employee's allocation from the department's unallocated pool and set the status to "approved".
- REQ-53 [unwanted] If the department pool is insufficient, then the system shall block approval with "Not enough unallocated department budget".
- REQ-54 [event] When a Manager/Admin rejects a request with a note, the system shall set the status to "rejected" and show the note to the employee.
- REQ-55 [event] When an Employee cancels their own pending request, the system shall set the status to "cancelled".
- REQ-56 [always] An Employee shall see only their own allocation and requests on Resource Allocation; a Manager shall see only their department.
- REQ-57 [always] Every lending and allocation action shall write a notification record for the affected user, and an audit log entry (the notification UI comes in Phase 4) (interpreted).
- REQ-58 [always] After any allocation change, the Overview, AI Usage and reconcile.py figures shall stay consistent (allocations sum ≤ dept budget ≤ org budget).

## Quality requirements
Q-7  Tag: Integrity.Ledger
     Scale: balance mismatches between ledger history and displayed balances
     Meter: tester runs action sequences and recomputes; reconcile script extended to lending
     Must: 0
     Plan: 0
Q-8  Tag: Integrity.Concurrency
     Scale: double-applied accepts/approvals when an action is clicked twice quickly
     Meter: two parallel API calls on the same entry, 5 trials
     Must: 0 (second call returns 409)
     Plan: 0
Q-9  Tag: Security.Scope
     Scale: % of non-party / out-of-scope access attempts rejected
     Meter: curl with each demo role plus a second individual
     Must: 100%
     Plan: 100%
Q-10 Tag: Usability.Mobile
     Scale: lending request, accept and repay completed at 390px without horizontal scroll
     Meter: browser at 390px
     Must: all 3 flows complete
     Plan: same
Q-11 Tag: Trust.Disclaimer
     Scale: lending screens without the no-transfer disclaimer
     Meter: visual check
     Must: 0
     Plan: 0
Q-12 Tag: Performance.Action
     Scale: ms from submit to updated list
     Meter: browser timing, 3 trials
     Must: 1500
     Plan: 600
