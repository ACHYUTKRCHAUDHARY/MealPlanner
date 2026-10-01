from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.bootstrap import bootstrap
from app.db.models import Recipe
from app.db.session import engine


def test_bootstrap_preserves_existing_catalog():
    with Session(engine()) as db:
        recipe = db.scalar(select(Recipe))
        recipe_id = recipe.id
        recipe.data = dict(recipe.data, cost=123.45)
        db.commit()
    bootstrap()
    bootstrap()
    with Session(engine()) as db:
        assert db.get(Recipe, recipe_id).data['cost'] == 123.45
