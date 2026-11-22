# Orqestra

Orqestra connects AI resources, people and tasks so teams can decide who does which work, with which AI tool, and when.
It started as an Emergent prototype ("AI Resource Manager"). This version runs anywhere, with no Emergent services.

- **Stack:** React 19 (Create React App via craco, Tailwind, shadcn/Radix) + FastAPI + MongoDB.
- **One service:** FastAPI serves the API under `/api` and the built React app from the same origin.
- **Free by default:** no paid APIs. Task decomposition uses built-in rules; an LLM is optional (your own key).

## Demo accounts

Open the app and use the **one-click demo buttons** on the login page. No password needed.

| Role | Name | Email |
| --- | --- | --- |
| Organisation Admin | Daniel Okafor | daniel.okafor@nexora.io |
| Manager (Engineering) | Sofia Marchetti | sofia.marchetti@nexora.io |
| Employee (Engineering) | Arjun Mehta | arjun.mehta@nexora.io |
| Individual | Maya Ellison | maya.ellison@indie.dev |
| Individual friends | Tomás Reyes, Hana Sato, Kwame Boateng | tomas.reyes@ / hana.sato@ / kwame.boateng@indie.dev |

Email + password login also works for these accounts. The password is whatever you set as `DEMO_PASSWORD`.
Inside the app, demo users can switch role with **View as** in the top bar.

## Features

| Area | Status |
| --- | --- |
| **Tasks: goal → sub-tasks** (rule-based breakdown for software, research, content, design, data, launch and general work; optional LLM) | Implemented |
| **Sub-task dependencies and parallel waves** (loops rejected; a sub-task can't start until its dependencies are done) | Implemented |
| **Resource allocation suggestions** (top 3 people ranked by remaining capacity, experience with the suggested tool, workload and team, each with reasons) | Implemented |
| **Planner slot suggestions** (first free weekday slot in working hours before the deadline, after dependencies, avoiding existing sessions, after a known reset for heavy work) | Implemented |
| Add a suggested slot to the planner (assignee) or send it to the assignee (owner) | Implemented |
| Output consolidation (sub-task outputs → goal summary → close goal) | Implemented |
| "Out of capacity" options (request internal budget, reallocate, hand over); never a provider quota transfer | Implemented |
| Data labels (estimated by rules/LLM, entered by a person, Orqestra budget record, simulated usage, unavailable) | Implemented on Tasks |
| Overview, AI Usage, Reports (CSV) | Working, **simulated** usage data |
| Resource Allocation (budgets, reallocation, requests, suggestions incl. cross-department for admins) | Working (internal budget only) |
| Credit Lending between friends | Working, **simulated** obligations only, no provider credits move |
| Task Handover with attachments (stored in MongoDB GridFS) | Working |
| **Handover privacy:** admins/managers see metadata only; content and files only for sender and recipient | Implemented |
| Session Planner, reminders, provider reset times (entered by users), manager time suggestions | Working |
| Notifications, Team, Settings | Working |
| Integrations page | **Simulated** toggles (no real provider connections) |
| Google sign-in | Off by default (it relied on Emergent's auth service) |
| Real provider usage data, provider-side quota changes | Not implemented (see the audit) |

## Run locally

Requirements: Python 3.11+, Node 20+ with Yarn 1, MongoDB 6+ running on `localhost:27017`.

```bash
# backend
cd backend
python -m venv .venv && . .venv/bin/activate
pip install -r requirements-prod.txt          # or requirements.txt for tests and tools
cat > .env <<'ENV'
MONGO_URL=mongodb://127.0.0.1:27017
DB_NAME=orqestra
JWT_SECRET=change-me
DEMO_PASSWORD=Demo@12345
COOKIE_SECURE=false
FRONTEND_BUILD_DIR=../frontend/build
ENV

# frontend (build once; FastAPI serves it)
cd ../frontend && yarn install --frozen-lockfile && REACT_APP_BACKEND_URL="" yarn build

# start
cd ../backend && uvicorn server:app --port 8001
# open http://localhost:8001
```

The database seeds itself on first start (Nexora organisation, 90 days of simulated usage, demo goals).

## Environment variables

| Name | Required | Purpose |
| --- | --- | --- |
| `MONGO_URL` | yes | MongoDB connection string |
| `DB_NAME` | yes | Database name |
| `JWT_SECRET` | yes | Signs login tokens. Use a long random value |
| `DEMO_PASSWORD` | yes | Password for the seeded demo accounts |
| `COOKIE_SECURE` | no (default `true`) | Set `false` only for plain-HTTP local runs |
| `FRONTEND_BUILD_DIR` | no | Folder with the built React app; set in the Docker image |
| `CORS_ORIGINS` | no | Only needed if the frontend is served from a different origin |
| `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL` | no | Optional OpenAI-compatible LLM for decomposition (default model `gpt-4o-mini`). Without a key, the free rules are used |
| `ENABLE_EMERGENT_GOOGLE_AUTH` | no | Re-enables Emergent's Google sign-in (only works on Emergent) |

## Tests

```bash
cd backend
# needs the server running on :8001 with COOKIE_SECURE=false and DB_NAME=test_database, plus a backend/.env
REACT_APP_BACKEND_URL=http://localhost:8001 pytest tests e1_tests -q
BASE=http://localhost:8001 python e2e/ui_walkthrough.py     # browser walkthrough (Playwright + Chrome)
```

See `TEST_RESULTS.md` for the latest run and `DEPLOY.md` for free hosting on Render + MongoDB Atlas.
`memory/` holds Emergent's original build spec for reference only.
