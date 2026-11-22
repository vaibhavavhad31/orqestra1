# Phase 3 Journeys

(Task Handover and Session Planner are no longer placeholders; JRN-14 still holds for Notifications, Reports, Team, Integrations and Settings.)

## Task Handover
- JRN-52. steps: as Arjun, create a handover to a fellow Engineering member with title, objective, priority high, completed work, pending work, a context note and a PDF attachment. expected: it appears in Arjun's Sent and the assignee's Received as "pending"; the attachment downloads identical.
- JRN-53. steps: submit a handover without a title or pending work. expected: inline errors; nothing saved.
- JRN-54. steps: attach a .exe or a file over 10 MB. expected: "Unsupported file or file too large (max 10 MB)".
- JRN-55. steps: as Maya, assign a handover to a friend (Tomás); try assigning to an org user or a non-friend via the API. expected: the friend's handover works; the others get "You can't hand over to this user".
- JRN-56. steps: the assignee accepts, then marks complete with a note. expected: status pending → accepted → completed; the timeline shows each step with actor and time.
- JRN-57. steps: the assignee rejects another task with a reason. expected: "rejected" and the reason visible to the creator.
- JRN-58. steps: the creator cancels a pending task; the assignee tries to complete a still-pending task. expected: "cancelled"; the invalid transition returns 409.
- JRN-59. steps: a user who is neither party (e.g. a Marketing employee, or Hana for a Maya↔Tomás task) fetches the task or its attachment. expected: 403.
- JRN-60. steps: Sofia (Manager) opens All. expected: she sees Engineering handovers; Daniel (Admin) sees all org handovers.
- JRN-61. steps: open the Task Handover page. expected: the privacy note "Only the context you add here is shared. Your AI chat history is never shared." is visible; no chat-history field exists.

## Session Planner
- JRN-62. steps: as Maya, create a Claude session tomorrow 10:00 for 60 min, 50 credits, a reminder 30 min before. expected: it appears in the week view and the upcoming list at 10:00 local time after reload.
- JRN-63. steps: create a session in the past, with end before start, or with 0 credits. expected: inline errors.
- JRN-64. steps: create an overlapping session. expected: "Overlaps another session" warning; the session can still be saved.
- JRN-65. steps: edit, cancel and mark a session completed. expected: changes persist after reload.
- JRN-66. steps: add a provider reset time (ChatGPT, rolling 5 hours, next reset). expected: shown on the planner with "Entered by you".
- JRN-67. steps: create a session starting within the reminder window. expected: exactly one notification record "Upcoming session: …" is created.
- JRN-68. steps: as Sofia, open the Team view. expected: the Engineering members' sessions this week; the member filter works; no other departments. Daniel sees the whole org.
- JRN-69. steps: Sofia suggests a new time for Arjun's session; Arjun accepts. expected: Arjun is notified; on accept, the session time updates.
- JRN-70. steps: Arjun or Maya opens the team planner URL/API. expected: 403 / access denied state.
- JRN-71. steps: open the planner. expected: "Planning sessions does not create extra provider capacity or bypass usage limits." is visible.
- JRN-72. steps: at 390px, create a handover, accept it, and create a session. expected: works with no horizontal scroll; the planner shows a list layout.
- JRN-73. steps: after actions, check audit_log and notifications. expected: records exist for each action.
- JRN-74. steps: focused regression: demo logins, nav per role, lending accept, allocation approve, reconcile.py. expected: still pass.
