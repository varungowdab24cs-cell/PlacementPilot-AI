import logging
from collections.abc import Generator

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from backend.app.core.config import get_settings
from backend.app.models import Base

logger = logging.getLogger(__name__)
settings = get_settings()

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

if settings.database_url.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def enable_sqlite_foreign_keys(dbapi_connection, _) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def init_db() -> None:
    try:
        Base.metadata.create_all(bind=engine)
        _migrate_existing_student_table()
    except SQLAlchemyError as exc:
        logger.exception("Database initialization failed")
        raise RuntimeError("Unable to initialize the database") from exc


def _migrate_existing_student_table() -> None:
    table_migrations = {
        "students": {
        "password_hash": "VARCHAR(255) NOT NULL DEFAULT ''",
        "department": "VARCHAR(120)",
        "semester": "INTEGER",
        "programming_language_preference": "VARCHAR(80)",
        "target_company_categories": "JSON NOT NULL DEFAULT '[]'",
        "preparation_goals": "TEXT",
        },
        "questions": {
            "options": "JSON NOT NULL DEFAULT '[]'",
            "correct_answer": "VARCHAR(500) NOT NULL DEFAULT ''",
            "estimated_solving_time_seconds": "INTEGER NOT NULL DEFAULT 60",
            "is_sample": "BOOLEAN NOT NULL DEFAULT 0",
        },
        "student_answers": {
            "time_taken_seconds": "INTEGER NOT NULL DEFAULT 0",
        },
        "topics": {
            "prerequisite_topic_id": "INTEGER",
        },
        "topic_mastery": {
            "accuracy": "FLOAT",
            "consistency": "FLOAT",
            "practice_completion": "FLOAT",
            "assessment_count": "INTEGER NOT NULL DEFAULT 0",
            "mastery_level": "VARCHAR(30) NOT NULL DEFAULT 'Insufficient data'",
            "is_sufficient": "BOOLEAN NOT NULL DEFAULT 0",
        },
        "learning_paths": {
            "description": "TEXT",
        },
        "resources": {
            "platform": "VARCHAR(30)",
            "difficulty": "VARCHAR(20)",
            "official_url": "VARCHAR(500)",
            "prerequisite_topic_ids": "JSON NOT NULL DEFAULT '[]'",
            "recommended_company_categories": "JSON NOT NULL DEFAULT '[]'",
            "is_external": "BOOLEAN NOT NULL DEFAULT 0",
        },
        "practice_records": {
            "resource_id": "INTEGER",
            "outcome": "VARCHAR(20) NOT NULL DEFAULT 'attempted'",
            "solving_time_seconds": "INTEGER",
            "completion_source": "VARCHAR(30) NOT NULL DEFAULT 'self_reported'",
            "verified": "BOOLEAN NOT NULL DEFAULT 0",
        },
        "assessment_attempts": {
            "experiment_id": "INTEGER",
            "assessment_phase": "VARCHAR(20)",
        },
    }

    with engine.begin() as connection:
        existing_tables = set(inspect(connection).get_table_names())
        for table_name, columns in table_migrations.items():
            if table_name not in existing_tables:
                continue

            existing_columns = {
                column["name"] for column in inspect(connection).get_columns(table_name)
            }
            for column_name, column_definition in columns.items():
                if column_name not in existing_columns:
                    connection.execute(
                        text(
                            f"ALTER TABLE {table_name} ADD COLUMN "
                            f"{column_name} {column_definition}"
                        )
                    )


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Database session failed")
        raise
    finally:
        db.close()
