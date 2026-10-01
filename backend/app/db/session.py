from functools import lru_cache
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings


@lru_cache
def engine():
    url = settings().database_url
    for prefix in ('postgres://', 'postgresql://'):
        if url.startswith(prefix):
            url = url.replace(prefix, 'postgresql+psycopg://', 1)
    kwargs = {'connect_args': {'check_same_thread': False}} if url.startswith('sqlite') else {}
    return create_engine(url, pool_pre_ping=True, hide_parameters=True, **kwargs)


def session():
    with sessionmaker(engine(), expire_on_commit=False)() as db:
        try:
            yield db
        except Exception:
            db.rollback()
            raise
