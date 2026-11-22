# Deploying Orqestra for free (Render + MongoDB Atlas)

Result: one public URL such as `https://orqestra.onrender.com` that an evaluator can open and log into with the demo buttons.
Cost: $0. Time: about 30 minutes. No Emergent credits.

Free-tier facts to know:
- Render's free web service **sleeps after 15 idle minutes**; the next visit takes up to about a minute to wake. Open the link a minute before a demo.
- MongoDB Atlas's free cluster has **512 MB** of storage. Orqestra's seed data uses a few MB.
- Session reminders only run while the service is awake.

## 1. Create the database (MongoDB Atlas, about 10 minutes)

1. Sign up or sign in at https://www.mongodb.com/cloud/atlas/register.
2. Create a **free** cluster (choose the Free option and any region close to you).
3. **Database Access** → add a database user with a username and a strong password (password authentication). Save both.
4. **Network Access** → **Add IP Address** → **Allow access from anywhere** (`0.0.0.0/0`). Render's free tier has no fixed IP address, so this is needed. The database user's password protects the data.
5. **Connect** → **Drivers** → copy the connection string. It looks like
   `mongodb+srv://<user>:<password>@<cluster>.mongodb.net/?retryWrites=true&w=majority`
   Replace `<password>` with your user's password. Keep this string private.

## 2. Put the code in a GitHub repository (about 5 minutes)

Render deploys from Git. Use a **new, empty** repository so the original stays untouched as your rollback.

1. On GitHub: **New repository** → name it `orqestra` → Private or Public → **Create** (don't add a README).
2. Unzip `orqestra-release.zip` on your computer.
3. Upload the files:
   - **With Git installed:** in the unzipped folder run
     `git init && git add . && git commit -m "Orqestra release" && git branch -M main && git remote add origin https://github.com/<you>/orqestra.git && git push -u origin main`
   - **Without Git:** on the empty repository page click **uploading an existing file**, drag in the *contents* of the unzipped folder, and commit. GitHub's web upload accepts at most 100 files at a time, so upload in a few batches (for example `backend/`, then `frontend/src/`, then the remaining files). Keep the folder structure.

## 3. Create the Render service (about 10 minutes)

1. Sign up at https://render.com (GitHub sign-in is easiest; no credit card is needed for the free plan).
2. **New** → **Blueprint** → connect your GitHub account and pick the `orqestra` repository. Render reads `render.yaml`.
   (Alternative: **New → Web Service** → pick the repository → Runtime **Docker** → Instance type **Free**, then add the variables below by hand.)
3. Render asks for the variables marked as secret:
   - `MONGO_URL`: the Atlas connection string from step 1.5
   - `DEMO_PASSWORD`: any password for the demo accounts (for example a long random phrase). Evaluators don't need it; they use the demo buttons.
   - `LLM_API_KEY`: **leave empty** to stay free (the built-in rules are used).
   `JWT_SECRET` is generated automatically. `DB_NAME=orqestra` and `COOKIE_SECURE=true` are preset.
4. **Apply / Create**. The first build takes roughly 5–10 minutes (it builds the React app and the Python image).
5. When the status shows **Live**, open the URL Render shows. `https://<name>.onrender.com/api/health` should return `{"status":"ok"}`.

## 4. Check it (5 minutes)

- Login page shows **Orqestra** and demo buttons; no Google button.
- Manager demo → **Tasks** → **New goal** → **Break down into sub-tasks** → **Create goal** → **Suggest assignee** → **Assign** → **Suggest slot**.
- Admin demo → **Task Handover** → **All** → open a handover between other people: content is hidden ("visible to the sender and recipient only").
- Admin demo → **Resource Allocation**: suggested reallocations appear.

## Updating later

Push changes to the repository; Render redeploys automatically. Data stays in Atlas.

## Rollback

- The original Emergent project and its GitHub repository (`ai-quota-hub`) are untouched.
- On Render, **Events / Deploys** lists every deploy; use **Rollback** on an earlier one.
- To start the data again from the seed, drop the `orqestra` database in Atlas and restart the Render service.

## Optional: LLM decomposition (costs money with most providers)

Set `LLM_API_KEY` (and optionally `LLM_BASE_URL`, `LLM_MODEL`) on Render. Any OpenAI-compatible endpoint works.
Only the goal title, priority and details that a user types are sent. The token count is shown after each breakdown.
If the call fails, Orqestra falls back to the free rules.
