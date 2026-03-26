import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from shortener.db import (
    dispose_engine,
    get_db,
    get_engine,
    get_session_factory,
    init_db,
    session_scope,
)
from shortener.models import ShortLink


def test_database_url_uses_postgres_settings(monkeypatch) -> None:
    class FakeSettings:
        user = "appuser"
        password = "secret:word"
        host = "db.internal"
        port = 5432
        database = "shortener"

    monkeypatch.setattr("shortener.db.get_settings", lambda: FakeSettings())
    import shortener.db as db_mod

    url = db_mod._database_url()
    assert url.drivername == "postgresql+psycopg"
    assert url.username == "appuser"
    assert url.password == "secret:word"
    assert url.host == "db.internal"
    assert url.port == 5432
    assert url.database == "shortener"


def test_get_engine_returns_singleton(sqlite_engine) -> None:
    dispose_engine()
    init_db()
    a = get_engine()
    b = get_engine()
    assert a is b


def test_dispose_engine_resets_singleton(sqlite_engine) -> None:
    e1 = get_engine()
    dispose_engine()
    init_db()
    e2 = get_engine()
    assert e1 is not e2


def test_init_db_creates_short_links_table(sqlite_engine) -> None:
    with sqlite_engine.connect() as conn:
        names = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
        table_names = {row[0] for row in names}
    assert "short_links" in table_names


def test_short_links_table_has_title_column(sqlite_engine) -> None:
    with sqlite_engine.connect() as conn:
        cols = conn.execute(text("PRAGMA table_info(short_links)"))
        column_names = {row[1] for row in cols}
    assert "title" in column_names


def test_get_db_yields_session_and_closes(sqlite_engine) -> None:
    gen = get_db()
    session = next(gen)
    assert isinstance(session, Session)
    assert session.is_active
    with pytest.raises(StopIteration):
        next(gen)
    with pytest.raises(StopIteration):
        next(gen)
    assert not session.in_transaction()


def test_session_scope_commits(sqlite_engine) -> None:
    with session_scope() as s:
        s.add(
            ShortLink(
                code="c1",
                url="https://committed.example/",
                title="Committed — Example",
            )
        )
    factory = get_session_factory()
    with factory() as s2:
        row = s2.get(ShortLink, "c1")
        assert row is not None
        assert row.url == "https://committed.example/"
        assert row.title == "Committed — Example"


def test_session_scope_rollback_on_error(sqlite_engine) -> None:
    with pytest.raises(RuntimeError, match="fail"):
        with session_scope() as s:
            s.add(ShortLink(code="rb", url="https://rollback.example/"))
            raise RuntimeError("fail")
    factory = get_session_factory()
    with factory() as s2:
        assert s2.get(ShortLink, "rb") is None
