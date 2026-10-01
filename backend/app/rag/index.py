"""Run after seed/import: python -m app.rag.index. Resumable, model-aware."""
import json
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.ai.gemini import Gemini
from app.db.models import Recipe
from app.db.session import engine


def main():
    ai = Gemini()
    if not ai.config.gemini_api_key:
        raise SystemExit('Set GEMINI_API_KEY before embedding recipes.')
    with Session(engine()) as db:
        if db.bind.dialect.name != 'postgresql':
            raise SystemExit('Embedding indexing requires PostgreSQL + pgvector.')
        for recipe in db.scalars(select(Recipe)).all():
            if recipe.embedding is not None and recipe.embedding_model == ai.config.embedding_model:
                continue
            recipe.embedding = ai.embed(json.dumps(recipe.data), 'RETRIEVAL_DOCUMENT')
            recipe.embedding_model = ai.config.embedding_model
            db.commit()
            print(f'Indexed {recipe.name}')


if __name__ == '__main__':
    main()
