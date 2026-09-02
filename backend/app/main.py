from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.schemas import PlanRequest, PlanResponse
from app.services.planner import MealPlanner

app = FastAPI(title="Plateful API", version="1.0.0", description="Grounded Indian meal planning API")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5500","http://localhost:5173"], allow_methods=["*"], allow_headers=["*"])
planner = MealPlanner()

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "UP"}

@app.post("/api/v1/plans/generate", response_model=PlanResponse)
def generate_plan(request: PlanRequest) -> PlanResponse:
    return planner.create(request)
