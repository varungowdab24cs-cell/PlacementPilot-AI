import os

import pytest

os.environ.setdefault(
    "JWT_SECRET_KEY",
    "test-only-jwt-secret-key-that-is-long-enough-for-tests",
)
os.environ.setdefault("RESEARCHER_API_KEY", "test-researcher-key")

from backend.app.database import init_db


@pytest.fixture(scope="session", autouse=True)
def initialize_database() -> None:
    init_db()
