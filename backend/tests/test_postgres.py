"""Run with TEST_DATABASE_URL pointing to a disposable PostgreSQL + pgvector DB."""
from unittest.mock import patch
import pytest
from sqlalchemy import select,text
from sqlalchemy.orm import Session
from app.db.models import Recipe
from app.db.session import engine
from app.ai.gemini import Gemini
from app.rag.retriever import catalog,retrieve
from app.core.config import settings
from test_planner import request


def test_real_pgvector_filter_and_distance(monkeypatch):
    if engine().dialect.name!='postgresql':
        pytest.skip('Requires PostgreSQL; CI runs this against pgvector/pgvector:pg16')
    monkeypatch.setattr(settings(),'gemini_api_key','mocked-embedding-provider')
    with Session(engine()) as db:
        assert db.execute(text("SELECT extversion FROM pg_extension WHERE extname='vector'")).scalar_one()
        for recipe in db.scalars(select(Recipe)).all():
            recipe.embedding=[1.0]+[0.0]*767
            recipe.embedding_model=settings().embedding_model
        db.commit()
        with patch.object(Gemini,'embed',return_value=[1.0]+[0.0]*767):
            scores,mode=retrieve(db,request(allergies=['soy']),catalog(db))
        assert mode=='pgvector' and scores
        safe=[r for r in catalog(db) if r['id'] in scores]
        assert all('vegan' in r['diet'] and 'soy' not in r['allergens'] for r in safe)
        assert all(abs(score-1)<1e-6 for score in scores.values())
