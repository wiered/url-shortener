import pytest

from shortener.settings import Settings, get_settings


@pytest.fixture(autouse=True)
def clear_settings_cache() -> None:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_settings_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOST", "127.0.0.1")
    monkeypatch.setenv("DATABASE", "db")
    monkeypatch.setenv("user", "u")
    monkeypatch.setenv("PASSWORD", "p")
    monkeypatch.setenv("PORT", "5432")
    monkeypatch.setenv("LOGGING_LEVEL", "INFO")
    monkeypatch.setenv("LOGGING_FORMAT", "json")

    s = Settings()
    assert s.host == "127.0.0.1"
    assert s.database == "db"
    assert s.user == "u"
    assert s.password == "p"
    assert s.port == 5432
    assert s.logging_level == "INFO"
    assert s.logging_format == "json"


def test_get_settings_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOST", "h")
    monkeypatch.setenv("DATABASE", "d")
    monkeypatch.setenv("user", "u")
    monkeypatch.setenv("PASSWORD", "pw")
    monkeypatch.setenv("PORT", "1")
    monkeypatch.setenv("LOGGING_LEVEL", "DEBUG")
    monkeypatch.setenv("LOGGING_FORMAT", "text")

    a = get_settings()
    b = get_settings()
    assert a is b
