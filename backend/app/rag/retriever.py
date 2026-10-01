import logging
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from app.db.models import Recipe
from app.ai.gemini import Gemini
from app.services.planner import eligible

log = logging.getLogger('plateful')


def catalog(db):
    return [row.data for row in db.scalars(select(Recipe)).all()]


def retrieve(db, request, recipes):
    """Hard-filter IDs before the database computes cosine distances.

    Return similarity scores, not a top-k safety/budget bottleneck. The planner
    retains the full eligible catalog so affordable recipes are never lost.
    """
    safe_ids = [r['id'] for r in recipes if eligible(r, request)]
    ai = Gemini()
    if not safe_ids or not ai.config.gemini_api_key or db.bind.dialect.name != 'postgresql':
        return {}, 'deterministic'
    try:
        vector = ai.embed('Indian meals; goals: ' + ', '.join(request.goals) + '; cuisine: ' + request.cuisine +
                          '; meal types: ' + ', '.join(request.meal_types), 'RETRIEVAL_QUERY')
        # Savepoint prevents a failed SQL query poisoning the plan-saving transaction.
        with db.begin_nested():
            distance = Recipe.embedding.cosine_distance(vector)
            rows = db.execute(select(Recipe.id, distance.label('distance')).where(
                Recipe.id.in_(safe_ids), Recipe.embedding.is_not(None),
                Recipe.embedding_model == ai.config.embedding_model).order_by(distance)).all()
        return {r.id: 1-float(r.distance) for r in rows}, 'pgvector' if rows else 'deterministic_no_embeddings'
    except Exception as error:
        log.warning('rag_fallback', extra={'event':'rag_fallback', 'error_type':type(error).__name__})
        return {}, 'deterministic_retrieval_unavailable'
