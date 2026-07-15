"""Entorno de Alembic.

Lee la URL de la base de datos desde la variable de entorno DATABASE_URL (la misma
que usa la app) y toma el metadata de los modelos SQLAlchemy para poder autogenerar
migraciones con `alembic revision --autogenerate`.
"""
import os
from logging.config import fileConfig

from sqlalchemy import create_engine
from alembic import context
from dotenv import load_dotenv

load_dotenv()

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata de los modelos para el autogenerate
from models import Base  # noqa: E402
target_metadata = Base.metadata

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("Falta DATABASE_URL para ejecutar las migraciones de Alembic.")


def run_migrations_offline() -> None:
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(DATABASE_URL, pool_pre_ping=True)
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
