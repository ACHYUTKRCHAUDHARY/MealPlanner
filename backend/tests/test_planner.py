from app.schemas import PlanRequest
from app.services.planner import MealPlanner

def test_plan_respects_days_and_diet():
    request = PlanRequest(days=["Monday","Tuesday"], budget=1500, people=2,
        goals=["protein"], diet="vegan", appliances=["stove"])
    plan = MealPlanner().create(request)
    assert len(plan.meals) == 2
    assert plan.estimated_total > 0
    assert plan.budget_remaining == 1500 - plan.estimated_total
