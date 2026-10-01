# Plateful Deployment Checklist

Before taking Plateful to production, ensure every item on this checklist is completed and verified.

## 1. Database & Persistence
- [ ] **Provision Managed PostgreSQL**: Use a managed database service (e.g., AWS RDS, Supabase, Neon, Render Database).
- [ ] **Enable pgvector**: Ensure the `vector` extension is installed and enabled in the database.
- [ ] **Configure SSL**: Verify that the database connection string uses SSL (the backend automatically appends `sslmode=require` in production).
- [ ] **Run Migrations**: Execute `python -m alembic upgrade head` against the production database using a dedicated migration role (not the web worker role if possible).
- [ ] **Seed Data**: Run `python -m app.db.seed` to load the initial recipe catalog. For production, ensure you are using a reviewed recipe set, not just the demonstration recipes.
- [ ] **Vector Indexing**: Run `python -m app.rag.index` against the production database to populate embeddings via Gemini.
- [ ] **Scheduled Backups**: Configure daily automated backups for the PostgreSQL database with point-in-time recovery (PITR) enabled.

## 2. Environment Variables & Secrets
- [ ] **DATABASE_URL**: Set the production PostgreSQL connection URI.
- [ ] **JWT_SECRET**: Generate a random string of at least 32 characters (e.g., `openssl rand -hex 32`) and set it in the environment. **Do not use the development secret.**
- [ ] **JWT_ALGORITHM**: Ensure this is set to `HS256`.
- [ ] **ENVIRONMENT**: Set to `production`.
- [ ] **FRONTEND_URL**: Set to the exact HTTPS Vercel origin (e.g., `https://plateful.vercel.app`).
- [ ] **CORS_ORIGINS**: Set to the exact HTTPS Vercel origin.
- [ ] **GEMINI_API_KEY**: Set the production Google Gemini API key.
- [ ] **RATE_LIMIT_PER_MINUTE**: Adjust based on expected load and Gemini API quota (default is 10).

## 3. Backend Deployment (Render / API)
- [ ] **Deploy Backend**: Deploy the FastAPI application to Render (or your chosen provider).
- [ ] **Health Check**: Verify that `/health` returns `{"status":"UP"}`.
- [ ] **Proxy Trust**: Configure trusted proxies if your backend is behind a load balancer or CDN to ensure rate limiting uses the actual client IP (not the proxy IP).
- [ ] **Concurrency**: Ensure your web workers (uvicorn) are scaled appropriately for expected traffic.

## 4. Frontend Deployment (Vercel / UI)
- [ ] **PUBLIC_API_URL**: Set this environment variable in Vercel to your production backend URL (e.g., `https://plateful-api.onrender.com`).
- [ ] **Deploy Frontend**: Trigger a production build on Vercel.
- [ ] **CSP Headers**: Review `vercel.json` to ensure the Content Security Policy allows connections only to your explicit production backend URL.

## 5. End-to-End Verification
Run through the application manually or using the smoke test script (`scripts/verify_live.py`) to confirm:
- [ ] Account registration and login work.
- [ ] Preferences and pantry data save correctly.
- [ ] Plan generation succeeds and returns realistic meals.
- [ ] The generated plan indicates `retrieval_mode=pgvector` and `ai_mode=gemini` (verifying AI is active).
- [ ] Swapping a meal works and updates the plan.
- [ ] Grocery checklists update properly.
- [ ] Email verification and password reset token generation function without errors.
- [ ] Account deletion cleanly removes the user and all associated data.
