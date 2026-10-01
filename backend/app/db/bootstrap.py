"""Serialized migration/bootstrap for a single free Render web service.

Use a separate pre-deploy migration job for a scaled deployment. Existing recipe
catalogs are never overwritten automatically; import reviewed updates explicitly.
"""
from pathlib import Path
from alembic import command
from alembic.config import Config
from sqlalchemy import select, func, text
from sqlalchemy.orm import Session
from app.db.session import engine
from app.db.models import Recipe
from app.db.seed import seed


def bootstrap():
    with engine().connect() as connection:
        postgres = connection.dialect.name == 'postgresql'
        if postgres:
            connection.execute(text('SELECT pg_advisory_lock(731604220)'))
        try:
            backend = Path(__file__).resolve().parents[2]
            config = Config(str(backend / 'alembic.ini'))
            config.set_main_option('script_location', str(backend / 'migrations'))
            command.upgrade(config, 'head')
            with Session(engine()) as db:
                if db.scalar(select(func.count()).select_from(Recipe)) == 0:
                    seed(db)
        finally:
            if postgres:
                connection.execute(text('SELECT pg_advisory_unlock(731604220)'))


if __name__ == '__main__':
    bootstrap()
