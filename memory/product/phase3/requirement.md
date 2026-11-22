# Phase 3: Task Handover & Session Planner (phase-3)

## Goal
Working task handover with attachments, and a session planner for Individual and Organisation users. Reuse the existing auth, RBAC, audit log, notification records and design system. Phases 1 and 2 must keep working, and seeded data must be preserved. See ../overview.md (F-13, F-14). Credit-lean: the simplest reliable implementation.

## Functional requirements

### Task Handover (all roles)
- REQ-59 [event] When a user creates a handover (title, description, objective, priority low/medium/high/urgent, completed work, pending work, context notes, optional attachments, assignee), the system shall save it with status "pending" and show it in the assignee's "Received" list.
- REQ-60 [unwanted] If the title, pending work or assignee is missing, then the system shall show an inline error.
- REQ-61 [always] Individuals shall only be able to assign to accepted friends; organisation users shall only be able to assign to active users in the same organisation.
- REQ-62 [unwanted] If the assignee is not allowed (another org, another mode, not a friend, self), then the system shall return 403/400 "You can't hand over to this user".
- REQ-63 [always] Attachments shall be stored in Emergent Object Storage (PDF, PNG, JPG, DOCX, TXT, MD; max 10 MB each, max 5 per task) and be downloadable only by the creator and the assignee (plus the Manager of the department and the Admin in an org).
- REQ-64 [unwanted] If a file has a wrong type or is over 10 MB, then the system shall show "Unsupported file or file too large (max 10 MB)".
- REQ-65 [event] When the assignee accepts, the system shall set the status to "accepted".
- REQ-66 [event] When the assignee rejects with a reason, the system shall set the status to "rejected" and show the reason to the creator.
- REQ-67 [event] When the assignee marks an accepted task complete (with an optional completion note), the system shall set the status to "completed".
- REQ-68 [event] When the creator cancels a pending task, the system shall set the status to "cancelled".
- REQ-69 [unwanted] If a status change is invalid for the current status or actor, then the system shall return 409/403 with no change.
- REQ-70 [always] Each task shall show a history timeline of every status change and edit, with actor and time.
- REQ-71 [always] Task visibility shall be: creator, assignee, and in orgs the department Manager (department view) and the Admin; nobody else (403).
- REQ-72 [always] The Task Handover page shall show tabs Received / Sent / All (All only for Manager and Admin), status filters, and a privacy note "Only the context you add here is shared. Your AI chat history is never shared."
- REQ-73 [always] The system shall never import or show AI chat history; there shall be no chat-history field.

### Session Planner (all roles)
- REQ-74 [event] When a user creates a session (provider, date/time, duration, estimated credits, purpose, optional reminder 15/30/60 min before), the system shall save it as "planned" on their calendar.
- REQ-75 [unwanted] If the end time is before the start time, the date is in the past, or the estimated credits are ≤ 0, then the system shall show an inline error.
- REQ-76 [unwanted] If a session overlaps another session of the same user, then the system shall show a warning "Overlaps another session" (still allowed) (interpreted).
- REQ-77 [always] Users shall be able to edit, cancel and mark sessions as completed.
- REQ-78 [always] Users shall record known provider reset times per provider (reset type: daily / weekly / monthly / rolling hours, next reset time), shown on the planner and labelled "Entered by you".
- REQ-79 [state] While a session's reminder time is reached, the system shall create an in-app notification record "Upcoming session: <purpose> at <time>" (exactly once).
- REQ-80 [always] The planner shall show a week view and an upcoming list, responsive at 390px (list on mobile).
- REQ-81 [always] A Manager (own department) and the Admin (org) shall see a Team view with all members' sessions for the week, filterable by member.
- REQ-82 [event] When a Manager suggests a new time for an employee's session with a note, the system shall store the suggestion and notify the employee, who can accept (time updated) or dismiss.
- REQ-83 [unwanted] If an Employee or Individual opens the team view or calls its API, then the system shall return 403.
- REQ-84 [always] The planner shall show "Planning sessions does not create extra provider capacity or bypass usage limits."
- REQ-85 [always] Every handover and session action shall write an audit log entry and a notification record for the affected user.
- REQ-86 [always] Seed shall add a few realistic handovers (Nexora and Maya↔friends) and sessions for the coming week, without changing existing seed records.

## Quality requirements
Q-13 Tag: Security.TaskScope
     Scale: % of non-authorised task/attachment/team-planner access attempts rejected
     Meter: curl with each demo role
     Must: 100%
     Plan: 100%
Q-14 Tag: Integrity.Attachments
     Scale: uploaded files that download byte-identical
     Meter: upload and download 3 files, compare hashes
     Must: 3/3
     Plan: 3/3
Q-15 Tag: Timezone.Sessions
     Scale: sessions shown at the wrong local time
     Meter: create a session in the browser, reload, check the time
     Must: 0
     Plan: 0
Q-16 Tag: Usability.Mobile
     Scale: handover create/accept and session create completed at 390px without horizontal scroll
     Meter: browser
     Must: all
     Plan: all
