from logging.config import fileConfig
from sqlalchemy import pool
from alembic import context

import os
import sys
from dotenv import load_dotenv

# ── Tell Python where to find your flask app ──
# __file__ is alembic/env.py
# os.path.dirname(__file__) is alembic/
# one more dirname gets you to flask-api/
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Load .env from the project root (one level above flask-api/)
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', '.env'))

# ── Alembic config object ─────────────────────
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ── Import your app and models ────────────────
# Alembic needs to see the models to autogenerate migrations
from app import create_app, db
from app.models import User, Review, RefreshToken

app = create_app()
target_metadata = db.metadata


# ── Offline mode (not used in this project) ───
def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


# ── Online mode (this is what actually runs) ──
def run_migrations_online() -> None:
    with app.app_context():
        connectable = db.engine
        with connectable.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                compare_type=True,
            )
            with context.begin_transaction():
                context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()