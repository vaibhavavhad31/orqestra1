# Phase 2 Journeys

superseded: [] (JRN-14 still holds for the modules not built in this phase; Credit Lending and Resource Allocation are no longer placeholders.)

## Credit Lending (Maya = individual demo; use a second individual account for counterparty actions, e.g. sign up a test individual or use demo friends if credentials exist)
- JRN-19. steps: as Maya, open Credit Lending. expected: summary cards, tabs All/Borrowed/Lent/Pending, the seeded entries, and "Obligation tracking only. No provider credits are transferred." visible.
- JRN-20. steps: as Maya, add a friend by the email of a newly signed-up individual; log in as that user and accept. expected: both see each other in Friends.
- JRN-21. steps: add a friend using an organisation employee's email or an unknown email. expected: "No individual user found with that email".
- JRN-22. steps: Maya requests 100 credits from the new friend with a reason. expected: pending entry visible to both; no balance change yet.
- JRN-23. steps: the friend accepts. expected: status "active"; the friend's available drops by 100 and Maya's rises by 100; Maya's Overview reflects this.
- JRN-24. steps: the friend tries to accept a request bigger than their available credits. expected: "Not enough available credits to lend"; status stays pending.
- JRN-25. steps: request with an amount of 0, -5 or 2.5. expected: inline error; nothing created.
- JRN-26. steps: Maya sends a lend offer; the friend declines. expected: status "declined"; balances unchanged.
- JRN-27. steps: Maya creates a request and then cancels it. expected: status "cancelled".
- JRN-28. steps: Maya (borrower) records a repayment of 40 of 100; the lender confirms. expected: outstanding 60; loan still active; timeline shows the repayment.
- JRN-29. steps: Maya tries to repay 80 when 60 is outstanding. expected: "Repayment exceeds outstanding amount".
- JRN-30. steps: repay the remaining 60; the lender confirms. expected: status "repaid"; outstanding 0.
- JRN-31. steps: the lender disputes a recorded repayment. expected: status "disputed"; outstanding unchanged.
- JRN-32. steps: a third individual (not a party) fetches the entry by id; an org user calls lending APIs. expected: 403 in both cases.
- JRN-33. steps: fire the accept action twice in parallel. expected: one succeeds and the other returns 409; the balance changes once.
- JRN-34. steps: view an active loan past its due date. expected: "Overdue" badge.
- JRN-35. steps: do the request, accept and repay flow at 390px. expected: completes with no horizontal scroll.

## Resource Allocation
- JRN-36. steps: as Admin, open Resource Allocation. expected: org budget, department budgets, a member table with allocation/used/remaining/utilisation/status, and an Underutilised panel with suggestions.
- JRN-37. steps: as Admin, raise one department budget so the total exceeds the org budget. expected: "Department budgets exceed organisation budget"; nothing saved.
- JRN-38. steps: as Manager (Sofia), set an Engineering member's allocation above the department budget. expected: "Allocations exceed department budget".
- JRN-39. steps: as Manager, reallocate 200 from an underutilised Engineering member to a near-limit one. expected: both rows update; utilisation statuses recompute; the change persists after reload.
- JRN-40. steps: as Manager, try to reallocate to a Marketing member, or move more than the source's unused allocation. expected: 403 / 400 with a clear error.
- JRN-41. steps: as Employee (Arjun), open Resource Allocation. expected: only his own allocation, usage and requests; no other members.
- JRN-42. steps: Arjun submits a request for 500 credits, reason "Release crunch", urgency high. expected: pending in his list and visible to Sofia and Daniel.
- JRN-43. steps: Arjun submits an empty reason or amount 0. expected: inline error.
- JRN-44. steps: Sofia approves 300 (partial). expected: status "approved"; Arjun's allocation +300; the department unallocated pool −300.
- JRN-45. steps: approve a request larger than the department's unallocated pool. expected: "Not enough unallocated department budget".
- JRN-46. steps: Sofia rejects a request with a note. expected: Arjun sees "rejected" and the note.
- JRN-47. steps: Arjun cancels his own pending request. expected: "cancelled".
- JRN-48. steps: as an Employee, call the allocation-update or approve API. expected: 403.
- JRN-49. steps: after the changes above, compare Overview, AI Usage and Allocation figures (and run reconcile.py). expected: all consistent; allocations ≤ dept budget ≤ org budget.
- JRN-50. steps: check the notifications and audit log collections after the actions. expected: a record exists for each affected user and action.
- JRN-51. steps: regression: rerun the Phase 1 checks (auth, nav, RBAC, switcher, usage, reconciliation, responsive). expected: all still pass.
