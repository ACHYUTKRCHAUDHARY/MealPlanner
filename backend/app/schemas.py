from enum import Enum
from pydantic import BaseModel, Field

class Diet(str, Enum):
    none = "none"
    vegetarian = "vegetarian"
    vegan = "vegan"
    eggetarian = "eggetarian"

class PlanRequest(BaseModel):
    days: list[str] = Field(min_length=1, max_length=7)
    budget: int = Field(ge=500, le=50000)
    people: int = Field(ge=1, le=12)
    goals: list[str] = Field(min_length=1, max_length=3)
    diet: Diet = Diet.none
    appliances: list[str] = Field(min_length=1)
    pantry: list[str] = []

class Meal(BaseModel):
    day: str
    name: str
    time_minutes: int
    estimated_cost: int
    calories: int
    protein_grams: int
    ingredients: dict[str, str]

class PlanResponse(BaseModel):
    meals: list[Meal]
    groceries: dict[str, str]
    estimated_total: int
    budget_remaining: int
    grounded: bool = True
