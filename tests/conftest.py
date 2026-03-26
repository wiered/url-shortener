from contextlib import asynccontextmanager

import pytest
import sqlalchemy as sa
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.testclient import TestClient

import shortener.models  # noqa: F401 — регистрация ShortLink в Base.metadata

from shortener.app import create_app
from shortener.db import Base, get_db


@asynccontextmanager
async def _empty_lifespan(_):
    yield


@pytest.fixture
def client() -> TestClient:
    engine = sa.create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app = create_app(lifespan=_empty_lifespan)
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as tc:
        yield tc
    app.dependency_overrides.clear()
    engine.dispose()


@pytest.fixture
def sqlite_engine(monkeypatch: pytest.MonkeyPatch):
    """Подменяет БД на SQLite в памяти для тестов shortener.db без PostgreSQL."""

    def patched_create_engine(url, **kwargs):
        if url.drivername == "sqlite":
            kwargs = {
                **kwargs,
                "connect_args": {
                    **kwargs.get("connect_args", {}),
                    "check_same_thread": False,
                },
            }
        return sa.create_engine(url, **kwargs)

    monkeypatch.setattr(
        "shortener.db._database_url",
        lambda: URL.create(drivername="sqlite", database=":memory:"),
    )
    monkeypatch.setattr("shortener.db.create_engine", patched_create_engine)

    from shortener.db import dispose_engine, get_engine, init_db

    dispose_engine()
    init_db()
    yield get_engine()
    dispose_engine()
