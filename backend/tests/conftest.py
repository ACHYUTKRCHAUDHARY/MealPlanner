import os
import tempfile
from pathlib import Path
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

TEST_PATH = Path(tempfile.mkdtemp()) / 'plateful.db'
os.environ['DATABASE_URL'] = os.getenv('TEST_DATABASE_URL', f'sqlite:///{TEST_PATH}')
os.environ['JWT_SECRET'] = 'test-only-secret-with-at-least-32-characters'
os.environ['ENVIRONMENT'] = 'test'
os.environ['RATE_LIMIT_PER_MINUTE'] = '1000'
os.environ['GEMINI_API_KEY'] = ''
from app.db.session import engine
from app.db.models import Base
from app.db.seed import seed
from app.main import app


@pytest.fixture(autouse=True)
def database():
    config=Config(str(Path(__file__).parents[1] / 'alembic.ini'))
    config.set_main_option('script_location',str(Path(__file__).parents[1] / 'migrations'))
    command.upgrade(config,'head')
    with engine().begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
    with Session(engine()) as db:
        seed(db)
    yield


@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client


@pytest.fixture
def authorized(client):
    response = client.post('/api/v1/auth/register',json={'email':'one@example.com','password':'a-secure-test-password'})
    assert response.status_code == 201, response.text
    return {'Authorization':'Bearer '+response.json()['access_token']}


@pytest.fixture
def preferences():
    return {'days':['Monday','Tuesday'],'budget':1000,'people':2,'goals':['protein'],'diet':'vegan',
            'appliances':['stove','pressure-cooker'],'meal_types':['dinner'],'pantry':[]}
