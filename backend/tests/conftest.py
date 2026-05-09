"""Shared pytest fixtures.

Strategy:
  * Build an in-memory SQLite database for unit tests via the same SQLAlchemy
    metadata. This keeps unit tests dependency-free and fast.
  * Integration tests that need Postgres-specific features (UUID, ARRAY, JSONB,
    INSERT...ON CONFLICT) are marked with `@pytest.mark.integration` and use a
    real Postgres URL from the QV_TEST_DATABASE_URL env var.
"""

from __future__ import annotations

import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db import get_db
from app.main import app
from app.models.base import Base


def _make_test_engine():
    url = os.getenv(
        "QV_TEST_DATABASE_URL",
        "sqlite:///:memory:",
    )
    if url.startswith("sqlite"):
        engine = create_engine(
            url,
            connect_args={"check_same_thread": False},
            future=True,
        )
    else:
        engine = create_engine(url, future=True, pool_pre_ping=True)
    return engine


@pytest.fixture(scope="session")
def test_engine():
    engine = _make_test_engine()
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def db(test_engine) -> Generator[Session, None, None]:
    """Per-test session with rollback. Each test starts with a clean slate."""
    connection = test_engine.connect()
    transaction = connection.begin()
    SessionTest = sessionmaker(bind=connection, autoflush=False, autocommit=False, future=True)
    session = SessionTest()
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def client(db) -> Generator[TestClient, None, None]:
    """TestClient with `get_db` overridden to use the per-test session."""

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()
