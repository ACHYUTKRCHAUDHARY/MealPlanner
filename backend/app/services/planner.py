import json
from pathlib import Path
from app.schemas import Meal, PlanRequest, PlanResponse

RECIPE_PATH = Path(__file__).parents[1] / "data" / "recipes.json"

class RecipeRetriever:
    """Deterministic retrieval layer; replace scoring with pgvector similarity in production."""
    def __init__(self) -> None:
        self.recipes = json.loads(RECIPE_PATH.read_text())

    def retrieve(self, request: PlanRequest) -> list[dict]:
        eligible = [r for r in self.recipes if
            (request.diet.value == "none" or request.diet.value in r["diet"]) and
            set(r["appliances"]) & set(request.appliances)]
        eligible = eligible or self.recipes
        return sorted(eligible, key=lambda r: (
            -len(set(r["goals"]) & set(request.goals)), r["cost"]
        ))

class MealPlanner:
    def __init__(self) -> None:
        self.retriever = RecipeRetriever()

    def create(self, request: PlanRequest) -> PlanResponse:
        candidates = self.retriever.retrieve(request)
        meals, groceries = [], {}
        for index, day in enumerate(request.days):
            recipe = candidates[index % len(candidates)]
            cost = round(recipe["cost"] * request.people / 2)
            meals.append(Meal(day=day, name=recipe["name"], time_minutes=recipe["time_minutes"],
                estimated_cost=cost, calories=recipe["calories"], protein_grams=recipe["protein_grams"],
                ingredients=recipe["ingredients"]))
            groceries.update(recipe["ingredients"])
        total = sum(meal.estimated_cost for meal in meals)
        return PlanResponse(meals=meals, groceries=groceries, estimated_total=total,
            budget_remaining=max(0, request.budget-total))
