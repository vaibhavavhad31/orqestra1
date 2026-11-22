# Phase 1 Journeys

- JRN-1. steps: open the app logged out. expected: login page shows email/password form, "Continue with Google", and 4 demo login buttons (Organisation Admin, Manager, Employee, Individual).
- JRN-2. steps: enter a wrong password and submit. expected: "Invalid email or password" shown; user stays on login.
- JRN-3. steps: sign up with a new email, password ≥8 chars, choose Individual mode. expected: lands on the Overview page with the Individual navigation (no Team, no Resource Allocation); refreshing keeps the session.
- JRN-4. steps: sign up with an existing email or a 5-char password. expected: inline field error; no account created.
- JRN-5. steps: click the "Organisation Admin" demo login. expected: Overview shows Nexora Technologies, org budget used/remaining cards and spend by department chart; sidebar shows 10 modules (no Credit Lending).
- JRN-6. steps: click the Manager demo login. expected: Overview shows the manager's department team usage; sidebar has no Credit Lending or Integrations.
- JRN-7. steps: click the Employee demo login. expected: Overview shows personal credits used/remaining; sidebar shows only Overview, AI Usage, Resource Allocation, Task Handover, Session Planner, Notifications, Settings.
- JRN-8. steps: click the Individual demo login. expected: Overview shows personal credits and a lending summary; sidebar includes Credit Lending, excludes Team and Resource Allocation.
- JRN-9. steps: as a demo user, open "View as role" and pick Manager. expected: session switches to the manager account; navigation and Overview update without manual login.
- JRN-10. steps: as Employee, type the /team URL directly. expected: "You don't have access to this page" state; the API call to team endpoints returns 403.
- JRN-11. steps: as Individual, call an org endpoint (e.g. org departments) with the individual token. expected: 403.
- JRN-12. steps: as Admin, open AI Usage, switch range 7→30→90 days. expected: charts update by provider (ChatGPT, Claude, Gemini, Copilot, Perplexity); "Simulated data" label visible.
- JRN-13. steps: as Employee, open AI Usage. expected: only own usage shown; no other employee names visible.
- JRN-14. steps: open Credit Lending, Task Handover, Session Planner, Notifications, Reports, Team, Integrations, Settings as the appropriate role. expected: each shows a polished placeholder with module name, purpose, and "Coming in a later phase".
- JRN-15. steps: open Overview and AI Usage at 390px width. expected: sidebar collapses into a drawer via a menu button; cards stack; no horizontal overflow.
- JRN-16. steps: click Log out. expected: returned to login; visiting /overview redirects to login.
- JRN-17. steps: as Admin, check Overview data against the DB. expected: figures come from the API (not hardcoded); Nexora has ~12 employees across 4 departments.
- JRN-18. steps: click "Continue with Google". expected: redirects to the Emergent Google auth flow (completing it is human-verified); a first-time Google user is asked to pick Individual or Organisation.
