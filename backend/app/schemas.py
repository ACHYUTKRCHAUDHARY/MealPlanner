from enum import Enum
from typing import Literal
from pydantic import BaseModel, Field, EmailStr, ConfigDict, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class Diet(str, Enum):
    none = 'none'
    vegetarian = 'vegetarian'
    vegan = 'vegan'
    eggetarian = 'eggetarian'


MealType = Literal['breakfast', 'lunch', 'dinner', 'snack']
Day = Literal['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
Allergy = Literal['dairy', 'peanuts', 'tree nuts', 'gluten', 'soy', 'egg']


class Quantity(StrictModel):
    name: str = Field(min_length=1, max_length=100)
    quantity: float | None = Field(default=None, ge=0, le=1000000, allow_inf_nan=False)
    unit: Literal['g', 'kg', 'ml', 'L', 'piece', 'count', 'bunch', 'bulb'] = 'g'


class PlanRequest(StrictModel):
    days: list[Day] = Field(min_length=1, max_length=7)
    budget: float = Field(ge=1, le=50000, allow_inf_nan=False)
    people: int = Field(ge=1, le=12)
    goals: list[str] = Field(default_factory=list, max_length=3)
    diet: Diet = Diet.none
    appliances: list[str] = Field(min_length=1, max_length=12)
    pantry: list[str] = Field(default_factory=list, max_length=100)
    pantry_quantities: list[Quantity] = Field(default_factory=list, max_length=100)
    allergies: list[Allergy] = Field(default_factory=list, max_length=6)
    exclusions: list[str] = Field(default_factory=list, max_length=50)
    meal_types: list[MealType] = Field(default_factory=lambda: ['dinner'], min_length=1, max_length=4)
    cuisine: str = Field(default='Indian', max_length=100)

    @field_validator('days', 'meal_types')
    @classmethod
    def unique(cls, value):
        if len(set(value)) != len(value):
            raise ValueError('Duplicate selections are not allowed')
        return value

    @field_validator('goals', 'appliances', 'pantry', 'exclusions')
    @classmethod
    def bounded_text(cls, value):
        if any(not s.strip() or len(s) > 100 for s in value):
            raise ValueError('Values must contain 1–100 characters')
        return [s.strip().lower() for s in value]

    @model_validator(mode='after')
    def pantry_unique(self):
        from app.services.ingredients import normalize
        names = [normalize(q.name) for q in self.pantry_quantities]
        if len(names) != len(set(names)):
            raise ValueError('Use one pantry quantity per ingredient')
        return self


class Meal(BaseModel):
    id: str
    recipe_id: str
    day: str
    meal_type: MealType
    name: str
    time_minutes: int
    estimated_cost: float
    calories: float | None
    protein_grams: float | None
    ingredients: dict[str, str]
    instructions: list[str] = Field(default_factory=list)


class PlanResponse(BaseModel):
    id: str | None = None
    meals: list[Meal]
    groceries: dict[str, str]
    grocery_items: list[Quantity]
    estimated_total: float
    budget_remaining: float
    nutrition_totals: dict
    grounded: bool = True
    retrieval_mode: str = 'deterministic'
    explanation: str = ''
    ai_mode: str = 'deterministic'
    warnings: list[str] = Field(default_factory=list)
    saved: bool = False


class Credentials(StrictModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)

    @field_validator('email')
    @classmethod
    def email_lower(cls, value):
        return str(value).lower()


class SavePlan(StrictModel):
    plan_id: str = Field(min_length=36, max_length=36)


class EmailOnly(StrictModel):
    """Used for password reset requests where only the email is needed."""
    email: EmailStr

    @field_validator('email')
    @classmethod
    def email_lower(cls, value):
        return str(value).lower()


class ResetPassword(StrictModel):
    token: str = Field(min_length=1, max_length=100)
    new_password: str = Field(min_length=12, max_length=128)


class VerifyEmail(StrictModel):
    token: str = Field(min_length=1, max_length=100)


class PantryRequest(StrictModel):
    items: list[Quantity] = Field(max_length=100)

    @model_validator(mode='after')
    def unique(self):
        keys = [i.name.casefold() for i in self.items]
        if len(keys) != len(set(keys)):
            raise ValueError('Duplicate pantry ingredients')
        return self


class CheckedRequest(StrictModel):
    checked: bool
