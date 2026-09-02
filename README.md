# Plateful — AI-ready Indian Meal Planner

Plateful is a responsive meal-planning app inspired by the supplied mobile flow. Users choose cooking days, budget, goals, diet, appliances and pantry items, then receive a weekly plan with nutrition, costs and an aggregated grocery list.

## What works

- Six-step responsive planning flow with local auto-save
- Budget and serving controls
- Dietary, goal and appliance constraints
- Grounded recipe retrieval instead of invented nutrition data
- Weekly meal dashboard, grocery checklist and print view
- FastAPI endpoint with Pydantic validation and OpenAPI docs
- Deterministic RAG-ready retrieval service and recipe knowledge base
- Docker setup and unit test

## Run the frontend

Open `frontend/index.html`, or run:

```bash
python -m http.server 5500 --directory frontend
```

Visit `http://localhost:5500`.

## Run the API

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

API docs: `http://localhost:8000/docs`

## API example

`POST /api/v1/plans/generate`

```json
{"days":["Monday","Tuesday"],"budget":1800,"people":2,"goals":["protein"],"diet":"vegetarian","appliances":["stove","pressure-cooker"],"pantry":["rice","onion"]}
```

## Architecture

The current retrieval layer filters a trusted recipe knowledge base by hard constraints and ranks candidates by user goals. It is intentionally deterministic and testable. For production RAG, move recipes to PostgreSQL + pgvector, embed recipe descriptions, retrieve semantic candidates, then keep diet, allergen and budget validation as deterministic code around the LLM.

## Next production upgrades

1. PostgreSQL + pgvector persistence
2. Gemini structured output for explanations and substitutions
3. JWT authentication and saved plan history
4. n8n for scheduled weekly plans and notifications
5. Receipt OCR and actual-versus-estimated spend tracking
