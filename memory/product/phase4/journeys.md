# Phase 4 Journeys

superseded: [JRN-14] (no placeholder modules remain after this phase)

## Notifications
- JRN-75. steps: log in as Sofia. expected: the bell shows an unread count; the dropdown lists the latest items; clicking one opens the related item.
- JRN-76. steps: mark one as read, then "Mark all as read". expected: the count drops by 1, then to 0; the state persists after reload.
- JRN-77. steps: Arjun submits a resource request. expected: within ~30s Sofia's bell count rises without a manual reload.
- JRN-78. steps: open Notifications as Maya. expected: All/Unread filter, and a "Pending actions" section with correct counts.
- JRN-79. steps: fetch or mark another user's notification via the API. expected: 403.

## Reports
- JRN-80. steps: as Admin, open Reports, view Usage and Allocation for 7/30/90. expected: tables and charts with "Simulated data"; totals match Overview/AI Usage.
- JRN-81. steps: click Export CSV for each report. expected: a CSV downloads with headers and the same totals.
- JRN-82. steps: as Sofia, export. expected: Engineering only. As Maya: personal usage and a lending summary, no Nexora data.
- JRN-83. steps: as Arjun, open /reports or call the API. expected: access denied / 403.

## Team
- JRN-84. steps: as Admin, open Team; search and filter by department. expected: correct members with role, department, status and allocation.
- JRN-85. steps: add a user (Employee, Marketing). expected: a temporary password is shown once; the new user can log in with it and sees Employee nav.
- JRN-86. steps: add a user with an existing email or a missing field. expected: inline error.
- JRN-87. steps: change that user's role to Manager. expected: after re-login they see Manager nav.
- JRN-88. steps: deactivate that user. expected: their login shows "Your account has been deactivated".
- JRN-89. steps: the Admin tries to deactivate or demote themselves or a demo account. expected: rejected with a message.
- JRN-90. steps: create and rename a department. expected: it persists and appears in the filters.
- JRN-91. steps: as Sofia, open Team. expected: Engineering members read-only, no add/edit controls; her calls to the team-management APIs return 403. Employee and Individual get 403.

## Integrations
- JRN-92. steps: as Maya and as Daniel, open Integrations. expected: 5 providers "Simulated, not connected"; the toggle shows "Simulated connection active" and the note "No real provider data is retrieved."; persists after reload.
- JRN-93. steps: as Sofia or Arjun, open /integrations. expected: access denied.

## Settings
- JRN-94. steps: edit name and title. expected: saved, and shown in the top bar after reload.
- JRN-95. steps: as a newly added (non-demo) user, change the password with a wrong current password, then correctly. expected: an inline error, then success; logging in with the new password works.
- JRN-96. steps: as a demo account, try to change the password. expected: "Password changes are disabled for demo accounts".
- JRN-97. steps: turn off "handover" notifications for a user, then hand a task to them. expected: no new handover notification created.
- JRN-98. steps: as Admin, rename the organisation. expected: the new name shows in the shell; rename it back to "Nexora Technologies" after the test.

## Final regression (major journeys)
- JRN-99. steps: rerun the major journeys: 4 demo logins plus nav per role, the RBAC 403 matrix, the View-as switcher, Overview/AI Usage reconciliation (reconcile.py), lending request→accept→repay, allocation request→approve, handover create→accept→complete with attachment, session create plus the team view, all Phase 4 pages at 390px. expected: all pass.
