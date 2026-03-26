import pytest
import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from shortener.db import Base
from shortener.models import ShortLink


@pytest.fixture
def model_session() -> Session:
    engine = sa.create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    session = factory()
    yield session
    session.close()
    engine.dispose()


def test_short_link_tablename() -> None:
    assert ShortLink.__tablename__ == "short_links"


def test_short_link_roundtrip(model_session: Session) -> None:
    row = ShortLink(code="abc12345", url="https://example.com/path")
    model_session.add(row)
    model_session.commit()

    loaded = model_session.get(ShortLink, "abc12345")
    assert loaded is not None
    assert loaded.url == "https://example.com/path"
    assert loaded.code == "abc12345"
    assert loaded.title is None


def test_short_link_stores_page_title_like_browser_tab(model_session: Session) -> None:
    row = ShortLink(
        code="yt01abcd",
        url="https://youtu.be/dQw4w9WgXcQ",
        title="Rick Astley - Never Gonna Give You Up (Official Video) - YouTube",
    )
    model_session.add(row)
    model_session.commit()

    loaded = model_session.get(ShortLink, "yt01abcd")
    assert loaded is not None
    assert loaded.title == "Rick Astley - Never Gonna Give You Up (Official Video) - YouTube"


def test_short_link_duplicate_code_raises(model_session: Session) -> None:
    model_session.add(ShortLink(code="dup", url="https://a.com"))
    model_session.commit()
    model_session.add(ShortLink(code="dup", url="https://b.com"))
    with pytest.raises(IntegrityError):
        model_session.commit()


def test_short_link_created_at_set(model_session: Session) -> None:
    model_session.add(ShortLink(code="t1", url="https://x.com"))
    model_session.commit()
    row = model_session.get(ShortLink, "t1")
    assert row is not None
    assert row.created_at is not None
