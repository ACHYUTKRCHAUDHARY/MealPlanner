# Plateful — Indian meal planning

Plateful connects a vanilla JavaScript meal-planning wizard to a FastAPI backend with PostgreSQL persistence, account ownership, pgvector recipe retrieval and optional Gemini-assisted explanations. The original lime/cream visual design is retained.

**Status:** implementation and local automated tests are available. The PostgreSQL 16/pgvector CI workflow passed. Hosted production and live Gemini still require deployment credentials and verification. See [verification and limitations](docs/IMPLEMENTATION.md). The bundled eight recipes use legacy, unverified nutrition and price estimates. They are a demonstration catalog, not a dietetic or medically validated source.

## Features

- Registration, login, current account and logout with Argon2 passwords and expiring JWTs.
- Backend-only meal selection. No frontend recipe database or offline fake-results fallback.
- Selected cooking days, people, meal types, diet, allergies, exclusions, appliances and goals.
- Hard constraints applied before similarity ranking; no diet/allergy relaxation.
- Budget-feasible baseline over the whole eligible catalog, then preference/variety improvements within budget.
- Pantry preference, measured quantity subtraction, compatible-unit conversion and grocery checklists.
- Saved history, protected account preferences/pantry, real swaps and persisted updated groceries.
- Daily/weekly nutrition for all people and selected meals. Unknown nutrients stay unknown.
- Real PostgreSQL cosine-distance retrieval using 768-dimensional recipe embeddings.
- Gemini selects schema-validated, fact-checked explanation highlights. Only trusted templates reach the UI; the model cannot change recipe facts or selections.
- Visible errors, retry controls, loading states, keyboard focus, mobile layout and print view.

## Architecture

```mermaid
flowchart TD
    UI["Vercel: HTML, CSS, JavaScript"] --> API["Render: FastAPI + JWT"]
    API --> DB["PostgreSQL: accounts, recipes, plans"]
    API --> Constraints["Diet, allergy and appliance filters"]
    Constraints --> Vector["pgvector: eligible recipe similarity"]
    Vector --> Planner["Budget, pantry and variety selection"]
    Planner --> AI["Gemini: validated explanation highlights"]
    AI --> API
    DB --- Vector
```

Runtime recipe source: PostgreSQL. `backend/app/data/recipes.json` is a versioned seed/import input, never a frontend dataset or request-time storage system. PostgreSQL recipe documents hold extensible metadata; normalized ingredient rows support inspection/integration. Import updates both transactionally and invalidates changed embeddings.

Stack: Python 3.12, FastAPI, Pydantic, SQLAlchemy, Alembic, psycopg, PostgreSQL + pgvector, Google Gemini REST API, Argon2, JWT, plain browser JavaScript. Node 22.22.2+ only builds the static frontend; there is no frontend runtime framework.

## Database

| Table | Main fields and relationships |
|---|---|
| users | UUID, unique indexed email, password hash, token version, timestamps |
| recipes | UUID, unique name, versioned recipe JSON, vector(768), embedding model, timestamps |
| recipe_ingredients | recipe FK, name, positive quantity, unit, nullable price per unit |
| user_preferences | unique user FK, validated preference JSON |
| pantry_items | user FK, normalized name, nullable quantity, unit; unique user/name/unit |
| meal_plans | user FK, saved flag, preference snapshot, response snapshot, timestamps |
| meal_plan_items | plan FK, recipe FK, day, meal type, servings; unique plan/day/type |
| grocery_lists | unique plan FK |
| grocery_items | list FK, name, nonnegative quantity, unit, checked state |
| rate_buckets | hashed client/bucket key + minute window; atomic request count |

Child data uses foreign keys/cascades; lookups are indexed. Plan swaps lock the owned plan row in PostgreSQL. Alembic migration `68640028cfbd` creates the schema and vector extension. The database role must be allowed to install pgvector, or the provider administrator must enable it beforehand. The migration intentionally does not drop the shared extension on downgrade.

Recipe fields include ID, name, description, cuisine, supported meal types/diets, ingredients, allergens, alternative **sets of required appliances**, timing, servings, estimated cost, nutrition, goals, instructions and provenance. `prep_time`, `cook_time`, missing nutrients and ingredient prices may be null. `time_minutes` is the known aggregate time. Original preparation instructions were absent and are not fabricated.

## RAG and AI behavior

1. Seed reviewed recipe documents to PostgreSQL.
2. `python -m app.rag.index` embeds recipe metadata with the configured Gemini embedding model and stores vectors/model version.
3. Requests hard-filter the catalog; eligible IDs become the SQL vector query's `WHERE` condition.
4. pgvector computes cosine similarity for those IDs. Semantic scores influence ranking, but the full safe catalog remains available for budget feasibility.
5. A deterministic planner selects meals and computes quantities/costs from stored data.
6. Gemini selects explanation reasons only from backend-provided valid options. Pydantic and membership validation reject unsupported IDs/reasons; safe templates render the explanation.

AI calls have timeouts and one retry for transient errors. Missing credentials, missing vectors, provider failures or invalid responses produce a **visible deterministic mode**, not a claim that RAG ran. A savepoint isolates vector query failure from plan persistence. Database outages return an error; they do not produce frontend recipes.

An exact vector scan is intentional for the small catalog; an approximate index is unnecessary here. Add and benchmark an HNSW index and SQL-native facet columns when the catalog grows substantially.

## Local setup — Windows PowerShell

Install Python 3.12, Git and Node 22.22.2+. Use a managed PostgreSQL database with pgvector, or a local PostgreSQL installation supporting the extension. Docker is optional, not required.

```powershell
git clone https://github.com/ACHYUTKRCHAUDHARY/MealPlanner.git
cd MealPlanner
# Check out the implementation branch/PR if it has not yet been merged.
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Edit `backend/.env`: set `DATABASE_URL`, replace `JWT_SECRET` with the generated value, and optionally configure `GEMINI_API_KEY`. Do not commit `.env`. Keep any SSL parameters required by your managed database, for example `?sslmode=require`. `postgres://` and `postgresql://` are adapted to psycopg automatically.

```powershell
python -m alembic upgrade head
python -m app.db.seed
# Only with a valid Gemini API key and PostgreSQL:
python -m app.rag.index
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

In a second terminal from the repository root:

```powershell
py -m http.server 5500 --directory frontend
```

Open `http://localhost:5500`. API docs: `http://localhost:8000/docs`. Register with an email and a 12–128 character password. Select preferences, generate, swap, save and open History. A page reload requires signing in again because access tokens are kept only in memory.

Pantry accepts comma-separated names, or one measured ingredient per line:

```text
rice: 500 g
onion: 3 count
curd: 200 g
```

A pantry name without a quantity boosts selection but never silently removes the entire ingredient from shopping. Quantities are snapshots for planning; the app does not consume inventory when generating or saving a plan.

To import a larger reviewed dataset:

```powershell
python -m app.db.seed --file path\to\reviewed-recipes.json
python -m app.rag.index
```

Use the bundled recipe schema as the format. Import validates documents, normalizes detected allergens and rejects obvious vegan dairy/egg conflicts. The importer upserts included recipe IDs without deleting other recipes. Never run the legacy seed after deliberately replacing those same IDs with reviewed data unless that replacement is intended.

## Environment variables

Backend reads `backend/.env` locally and environment variables in hosting.

| Variable | Required / default |
|---|---|
| DATABASE_URL | Required; PostgreSQL connection URI in production |
| JWT_SECRET | Required; random secret, at least 32 characters |
| JWT_ALGORITHM | HS256 only |
| ACCESS_TOKEN_EXPIRE_MINUTES | 60; range 5–1440 |
| ENVIRONMENT | development / test / production |
| FRONTEND_URL | localhost:5500 by default; exact HTTPS Vercel origin in production |
| CORS_ORIGINS | Comma-separated exact origins; explicit HTTPS only in production |
| GEMINI_API_KEY | Required for live embeddings and AI highlights; optional for deterministic operation |
| GEMINI_MODEL | gemini-2.5-flash; choose a supported model available to your account |
| EMBEDDING_MODEL | gemini-embedding-001; changing model requires reindexing |
| AI_TIMEOUT_SECONDS | 12 seconds per provider attempt |
| RATE_LIMIT_PER_MINUTE | 10 requests per client/minute for auth and separately expensive planning |
| PORT | Render supplies this to the start command |

Frontend build variable: **PUBLIC_API_URL**, e.g. `https://your-api.onrender.com`. This is public configuration. No Gemini key, DB URI or JWT secret belongs in Vercel/frontend files. Local source serving uses `frontend/config.js`'s localhost default. `npm run build` reads the shell environment; it does not automatically load the root `.env`.

## API

All data routes require `Authorization: Bearer <access_token>`. Authentication failures return 401; another user's object is indistinguishable from a missing object (404).

| Method | Endpoint | Purpose |
|---|---|---|
| GET | /health | DB/migration/extension readiness |
| POST | /api/v1/auth/register | Create account and token |
| POST | /api/v1/auth/login | Get access token |
| GET | /api/v1/auth/me | Current user |
| POST | /api/v1/auth/logout | Revoke all current user tokens |
| GET, PUT | /api/v1/users/me/preferences | Account preferences |
| GET, PUT | /api/v1/users/me/pantry | Measured pantry snapshot |
| POST | /api/v1/plans/generate | Generate and persist a draft plan |
| POST | /api/v1/plans | Save existing owned draft: `{"plan_id":"..."}` |
| GET | /api/v1/plans | Saved history; `limit` and `offset` |
| GET, DELETE | /api/v1/plans/{id} | Read/delete owned plan |
| POST | /api/v1/plans/{id}/items/{item_id}/swap | Replace with a different safe, budget-valid recipe |
| GET | /api/v1/plans/{id}/groceries | Grocery quantities and checklist IDs |
| PATCH | /api/v1/plans/{id}/groceries/{item_id} | Persist `{"checked":true}` |

Generation body:

```json
{"days":["Monday","Tuesday"],"budget":1000,"people":2,"goals":["protein"],"diet":"vegan","allergies":["dairy"],"exclusions":[],"appliances":["stove","pressure-cooker"],"meal_types":["dinner"],"pantry":["rice"],"pantry_quantities":[{"name":"rice","quantity":500,"unit":"g"}]}
```

If both pantry fields are omitted, generation loads the saved account pantry. An explicit empty pantry overrides it. Generating a plan persists a draft to enable swapping; **Save plan** adds it to history. Swap preserves the plan's original preference snapshot, updates nutrition and groceries atomically and resets grocery checks because requirements changed. Saved plans remain saved after swapping.

Errors have the shape `{"error":{"code":"budget_infeasible","message":"...","request_id":"..."}}`. Request IDs also appear in `X-Request-ID`.

## Render deployment

The repository's `render.yaml` defines a Python web service using an externally supplied PostgreSQL URL. The Blueprint selects a **free web service**; free-tier availability, sleep and resource limits depend on your account. This implementation does not create a paid resource automatically.

| Setting | Value |
|---|---|
| Root directory | backend |
| Runtime | Python 3.12 |
| Build | `pip install -r requirements.txt` |
| Database bootstrap | Runs serialized migrations and seeds only an empty catalog before serving |
| Start | `python -m app.db.bootstrap && python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT --no-access-log` |
| Health check | /health |
| Environment | ENVIRONMENT=production and backend variables above |

1. Provision a managed PostgreSQL database and enable `vector`. Use a TLS connection URI and a least-privilege runtime role; apply schema migrations with a migration role where appropriate.
2. Create the Render service via the Blueprint or manual settings. Set its DB URI, random JWT secret, Gemini key, and exact Vercel frontend URL/origins.
3. Deploy once. Confirm `/health` returns `{"status":"UP"}`.
4. From Render Shell or a trusted local terminal using the same DB URI/key, run `python -m app.rag.index`. This may incur Gemini API usage; it is not run automatically during deploy.
5. Generate a plan and verify `retrieval_mode=pgvector` and `ai_mode=gemini`. Then test temporary provider failure separately.

The free-service start command serializes migrations with a PostgreSQL advisory lock and seeds only an empty catalog. For scaled or zero-downtime deployments, move this work into a dedicated pre-deploy job and remove bootstrap from the start command. Do not run migrations concurrently from every web worker. Automatic deploy is off in the Blueprint until you enable your preferred release workflow.

Keep default proxy trust unless you have verified Render's proxy behavior. The app never trusts raw forwarded IP headers itself. Database-backed limiting is shared across workers; if requests all arrive with the same proxy IP, limits will be conservative/shared. Configure trusted proxy addresses deliberately; never accept arbitrary forwarded IP headers on an exposed backend.

## Vercel deployment

1. Import this repository. Set **Root Directory to the repository root**, not `frontend` or `dist`.
2. Framework preset: **Other**. Build command: `npm run build`. Output directory: `dist`.
3. Set `PUBLIC_API_URL=https://your-api.onrender.com` for each relevant deployment environment.
4. Deploy. Set Render's `FRONTEND_URL` and `CORS_ORIGINS` to that exact final Vercel HTTPS origin, then redeploy the backend.
5. Register, generate, swap, save, reload/sign in, and reopen history from the hosted site.

`frontend/` is the source of truth. `dist/` is generated and ignored. `scripts/build.mjs` rejects missing production API URLs and never embeds backend secrets. Static security headers are in `vercel.json`. Its CSP permits HTTPS API connections; tighten `connect-src` to your exact backend hostname if desired after deployment. Preview origins must be added explicitly; arbitrary `*.vercel.app` origins are not trusted.

## Testing

From repository root after installing backend development requirements:

```powershell
python -m pytest -q
npm ci
npm run check
npm run build
npm run test:ui
git diff --check
```

Default tests use a temporary SQLite database solely for fast unit/API verification. Production rejects SQLite. PostgreSQL-specific integration runs only when `TEST_DATABASE_URL` points to a **disposable** database: test fixtures clear application tables. Never use a production DB for tests.

```powershell
$env:TEST_DATABASE_URL="postgresql://test_user:password@localhost:5432/plateful_test"
python -m pytest -q
```

`.github/workflows/ci.yml` provides PostgreSQL 16 + pgvector and runs migrations, API tests, actual SQL vector retrieval with mocked provider vectors, frontend syntax/build and whitespace checks. This tests SQL/storage behavior; it is not a live Gemini smoke test. Unit tests also exercise AI failure and structured-output rejection.

## Security and data quality

- Argon2 password hashes, pinned JWT algorithm, issuer/audience/expiry checks and database-backed logout revocation.
- Ownership checks for all plans, swaps, groceries, preferences and pantry data.
- Parameterized ORM, bounded request schemas, 64 KiB body cap, exact-origin CORS and atomic DB rate limits.
- Structured request logs contain route templates, timings, request IDs and error class only; no passwords, bearer tokens, keys or raw SQL errors.
- Access tokens stay in browser memory. Preferences are saved locally as an explicit draft; logout clears the draft.
- Diet/allergy safety depends on correct, reviewed recipe and ingredient metadata. Packaged foods, mixed ingredients and cross-contact require independent label/preparation checks.
- For incomplete ingredient pricing, budget is conservatively based on whole-recipe cost, with no made-up pantry discount. When every ingredient is priced, purchases after pantry subtraction determine spend. Bounded exact feasibility search reports its limit honestly.
- No password reset/email verification, MFA, refresh token flow, account deletion UI or automated backup system is included. Configure provider backups, monitoring, retention and recovery before public launch.

For optional real-browser verification, install Chromium with `npx playwright-core install chromium`, then run `npm run test:browser`. Alternatively set `CHROME_PATH` to an installed Chromium executable. Browser checks generate ignored images in `test-results/`.

## Screenshots

Add reviewed desktop/mobile screenshots under `docs/screenshots/` after hosted smoke verification. This is a documentation placeholder, not a fake UI interaction.

## Remaining improvements

Reviewed recipes with complete preparation instructions, ingredient prices and cited nutrition; larger catalog/variety; finer nutritional targets; pantry inventory consumption; password reset and email verification; deployment smoke tests and monitoring. Natural-language preferences and AI substitutions are not enabled: all current substitutions go through the deterministic swap endpoint so they preserve constraints.

Official references: [Gemini embeddings](https://ai.google.dev/gemini-api/docs/embeddings), [Gemini structured output](https://ai.google.dev/gemini-api/docs/structured-output), [Render Blueprint specification](https://render.com/docs/blueprint-spec), [Vercel project configuration](https://vercel.com/docs/project-configuration).

## Hosted verification

Use a dedicated test account. Set `PLATEFUL_API_URL`, `PLATEFUL_TEST_EMAIL`, and `PLATEFUL_TEST_PASSWORD` in your terminal, then run `python scripts/verify_live.py --require-ai`. The script checks health, registration/login, preferences, pantry, generation, actual RAG/AI modes, swaps, history, grocery persistence and token revocation; it deletes its generated test plan. The test account remains available for future smoke tests.
