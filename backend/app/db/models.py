from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import String, ForeignKey, JSON, DateTime, Float, Integer, Boolean, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector


def uid():
    return str(uuid4())


class Base(DeclarativeBase):
    pass


class Identity:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class User(Identity, Base):
    __tablename__ = 'users'
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    token_version: Mapped[int] = mapped_column(default=0)
    preferences: Mapped['UserPreference'] = relationship(cascade='all, delete-orphan', uselist=False)
    plans: Mapped[list['MealPlan']] = relationship(cascade='all, delete-orphan')
    pantry: Mapped[list['PantryItem']] = relationship(cascade='all, delete-orphan')


class Recipe(Identity, Base):
    __tablename__ = 'recipes'
    name: Mapped[str] = mapped_column(String(200), unique=True)
    # Versioned recipe document contains extensible metadata; ingredients are normalized below.
    data: Mapped[dict] = mapped_column(JSON)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(768).with_variant(JSON(), 'sqlite'), nullable=True)
    embedding_model: Mapped[str | None] = mapped_column(String(100))
    ingredients: Mapped[list['RecipeIngredient']] = relationship(cascade='all, delete-orphan', lazy='selectin')


class RecipeIngredient(Identity, Base):
    __tablename__ = 'recipe_ingredients'
    __table_args__ = (CheckConstraint('quantity > 0'),)
    recipe_id: Mapped[str] = mapped_column(ForeignKey('recipes.id', ondelete='CASCADE'), index=True)
    name: Mapped[str] = mapped_column(String(100), index=True)
    quantity: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(20))
    unit_cost: Mapped[float | None] = mapped_column(Float)


class UserPreference(Identity, Base):
    __tablename__ = 'user_preferences'
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), unique=True)
    data: Mapped[dict] = mapped_column(JSON)


class MealPlan(Identity, Base):
    __tablename__ = 'meal_plans'
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    saved: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    preferences: Mapped[dict] = mapped_column(JSON)
    result: Mapped[dict] = mapped_column(JSON)
    items: Mapped[list['MealPlanItem']] = relationship(cascade='all, delete-orphan')
    grocery: Mapped['GroceryList'] = relationship(cascade='all, delete-orphan', uselist=False)


class MealPlanItem(Identity, Base):
    __tablename__ = 'meal_plan_items'
    __table_args__ = (UniqueConstraint('plan_id', 'day', 'meal_type'),)
    plan_id: Mapped[str] = mapped_column(ForeignKey('meal_plans.id', ondelete='CASCADE'), index=True)
    recipe_id: Mapped[str] = mapped_column(ForeignKey('recipes.id'), index=True)
    day: Mapped[str] = mapped_column(String(12))
    meal_type: Mapped[str] = mapped_column(String(12))
    servings: Mapped[int] = mapped_column(Integer)


class GroceryList(Identity, Base):
    __tablename__ = 'grocery_lists'
    plan_id: Mapped[str] = mapped_column(ForeignKey('meal_plans.id', ondelete='CASCADE'), unique=True)
    items: Mapped[list['GroceryItem']] = relationship(cascade='all, delete-orphan')


class GroceryItem(Identity, Base):
    __tablename__ = 'grocery_items'
    __table_args__ = (CheckConstraint('quantity >= 0'), UniqueConstraint('grocery_list_id', 'name', 'unit'))
    grocery_list_id: Mapped[str] = mapped_column(ForeignKey('grocery_lists.id', ondelete='CASCADE'), index=True)
    name: Mapped[str] = mapped_column(String(100))
    quantity: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(20))
    checked: Mapped[bool] = mapped_column(Boolean, default=False)


class PantryItem(Identity, Base):
    __tablename__ = 'pantry_items'
    __table_args__ = (CheckConstraint('quantity IS NULL OR quantity >= 0'), UniqueConstraint('user_id', 'name', 'unit'))
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    name: Mapped[str] = mapped_column(String(100))
    quantity: Mapped[float | None] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(20), default='g')


class RateBucket(Base):
    __tablename__ = 'rate_buckets'
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    window: Mapped[int] = mapped_column(Integer, primary_key=True)
    count: Mapped[int] = mapped_column(Integer, default=1)
