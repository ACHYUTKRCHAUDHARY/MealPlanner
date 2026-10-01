"""Idempotent import; recipe edits invalidate their embeddings. Never runs at startup."""
import json
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.models import Recipe, RecipeIngredient
from app.db.session import engine
from app.db.recipe_schema import RecipeDocument


def seed(db: Session, source: Path | None = None):
    data = json.loads((source or Path(__file__).parents[1] / 'data/recipes.json').read_text())
    data = [RecipeDocument.model_validate(row).model_dump(mode='json') for row in data]
    if len({row['id'] for row in data}) != len(data):
        raise ValueError('Duplicate recipe IDs in import')
    for document in data:
        row = db.get(Recipe, document['id'])
        if row and row.data == document:
            continue
        if not row:
            row = Recipe(id=document['id'], name=document['name'], data=document)
            db.add(row)
        row.data, row.name = document, document['name']
        row.embedding, row.embedding_model = None, None
        row.ingredients = [RecipeIngredient(name=i['name'], quantity=i['quantity'], unit=i['unit'], unit_cost=i.get('unit_cost')) for i in document['ingredients']]
    db.commit()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--file', type=Path, help='Reviewed recipe JSON to import instead of bundled seed')
    args = parser.parse_args()
    with Session(engine()) as db:
        seed(db,args.file)
        print(f'Recipes available: {len(db.scalars(select(Recipe)).all())}')
