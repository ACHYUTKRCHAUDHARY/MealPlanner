"""Validate reviewed recipe imports without inventing missing nutrition facts."""
from typing import Literal
from pydantic import Field, model_validator
from app.schemas import StrictModel, Quantity, MealType, Allergy
from app.services.ingredients import detected_allergens


class Ingredient(Quantity):
    quantity: float = Field(gt=0, le=1000000, allow_inf_nan=False)
    unit_cost: float | None = Field(default=None, ge=0, allow_inf_nan=False)


class RecipeDocument(StrictModel):
    id: str = Field(min_length=1,max_length=36)
    name: str = Field(min_length=1,max_length=200)
    description: str = Field(max_length=2000)
    cuisine: str = Field(max_length=100)
    diet: list[Literal['vegetarian','vegan','eggetarian','none']] = Field(min_length=1)
    goals: list[str] = Field(max_length=20)
    meal_types: list[MealType] = Field(min_length=1,max_length=4)
    appliance_options: list[list[str]] = Field(min_length=1,max_length=10)
    time_minutes: int = Field(ge=1,le=1440)
    prep_time: int | None = Field(default=None,ge=0)
    cook_time: int | None = Field(default=None,ge=0)
    servings: int = Field(ge=1,le=100)
    cost: float = Field(ge=0,allow_inf_nan=False)
    calories: float | None = Field(default=None,ge=0,allow_inf_nan=False)
    protein_grams: float | None = Field(default=None,ge=0,allow_inf_nan=False)
    carbohydrates: float | None = Field(default=None,ge=0,allow_inf_nan=False)
    fat: float | None = Field(default=None,ge=0,allow_inf_nan=False)
    fiber: float | None = Field(default=None,ge=0,allow_inf_nan=False)
    ingredients: list[Ingredient] = Field(min_length=1,max_length=100)
    allergens: list[Allergy]
    allergen_reviewed: bool = False
    allergen_note: str = Field(max_length=2000)
    instructions: list[str] = Field(max_length=50)
    nutrition_source: str = Field(min_length=1,max_length=2000)
    cost_source: str = Field(min_length=1,max_length=2000)

    @model_validator(mode='after')
    def safe_metadata(self):
        inferred=detected_allergens([i.model_dump() for i in self.ingredients])
        self.allergens=sorted(set(self.allergens)|inferred)
        if 'vegan' in self.diet and inferred & {'dairy','egg'}:
            raise ValueError('Vegan recipe has dairy/egg ingredients')
        if any(not option for option in self.appliance_options):
            raise ValueError('Each appliance option must list required appliances')
        return self
