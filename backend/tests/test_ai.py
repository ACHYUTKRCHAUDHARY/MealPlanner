from unittest.mock import patch
import httpx
from app.ai.gemini import Gemini
from app.core.config import settings
from app.services.planner import MealPlanner
from test_planner import RECIPES,request


def test_gemini_failure_keeps_safe_plan(monkeypatch):
    monkeypatch.setattr(settings(),'gemini_api_key','unit-test-only')
    result=MealPlanner(RECIPES).create(request())
    before=result.model_dump()
    with patch.object(Gemini,'post',side_effect=httpx.ReadTimeout('timeout')):
        after=Gemini().explain(result)
    assert after.meals==result.meals
    assert after.estimated_total==before['estimated_total']
    assert after.ai_mode=='deterministic'
    assert any('unavailable' in w for w in after.warnings)


def test_structured_explanation_rejects_unknown_ids(monkeypatch):
    monkeypatch.setattr(settings(),'gemini_api_key','unit-test-only')
    result=MealPlanner(RECIPES).create(request())
    with patch.object(Gemini,'post',return_value={'candidates':[{'content':{'parts':[{'text':'{"summary":"Fake","recipe_ids":["unknown"]}'}]}}]}):
        after=Gemini().explain(result)
    assert after.ai_mode=='deterministic'
    assert after.explanation!='Fake'


def test_embedding_dimensions_and_normalization(monkeypatch):
    monkeypatch.setattr(settings(),'gemini_api_key','unit-test-only')
    with patch.object(Gemini,'post',return_value={'embedding':{'values':[2.0]+[0.0]*767}}):
        vector=Gemini().embed('test','RETRIEVAL_QUERY')
    assert len(vector)==768 and vector[0]==1
