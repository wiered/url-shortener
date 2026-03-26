from contextlib import asynccontextmanager
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from shortener import app as app_module
from shortener.app import _random_code, create_app


@asynccontextmanager
async def _empty_lifespan(_: FastAPI):
    yield


def _no_fetch():
    return patch.object(app_module, "fetch_page_title", return_value=None)


def test_health_returns_ok(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_index_page_returns_html(client: TestClient) -> None:
    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")
    assert "URL Shortener" in r.text
    assert "/static/style.css" in r.text


def test_static_style_css_served(client: TestClient) -> None:
    r = client.get("/static/style.css")
    assert r.status_code == 200
    assert "text/css" in r.headers.get("content-type", "")
    assert ":root" in r.text


def test_shorten_returns_code_path_and_title(client: TestClient) -> None:
    with patch.object(app_module, "_random_code", return_value="abcXYZ12"), _no_fetch():
        r = client.post("/shorten", json={"url": "https://example.com/foo"})
    assert r.status_code == 200
    assert r.json() == {
        "code": "abcXYZ12",
        "path": "/r/abcXYZ12",
        "title": None,
    }


def test_shorten_accepts_trailing_slash(client: TestClient) -> None:
    with patch.object(app_module, "_random_code", return_value="slash01"), _no_fetch():
        r = client.post("/shorten/", json={"url": "https://example.com/a"})
    assert r.status_code == 200
    assert r.json()["code"] == "slash01"


def test_shorten_stores_title_from_body_without_fetch(client: TestClient) -> None:
    with patch.object(app_module, "_random_code", return_value="titled1") as _rc, patch.object(
        app_module, "fetch_page_title"
    ) as fetch_mock:
        r = client.post(
            "/shorten",
            json={
                "url": "https://example.com/x",
                "title": "My Page Title",
            },
        )
    assert r.status_code == 200
    fetch_mock.assert_not_called()
    assert r.json()["title"] == "My Page Title"
    gr = client.get("/links/recent")
    assert gr.status_code == 200
    assert gr.json()[0]["name"] == "My Page Title"


def test_shorten_uses_fetched_title_when_omitted(client: TestClient) -> None:
    with patch.object(app_module, "_random_code", return_value="fetch01"), patch.object(
        app_module,
        "fetch_page_title",
        return_value="Fetched From Web",
    ):
        r = client.post("/shorten", json={"url": "https://example.com/page"})
    assert r.status_code == 200
    assert r.json()["title"] == "Fetched From Web"


def test_redirect_after_shorten(client: TestClient) -> None:
    with patch.object(app_module, "_random_code", return_value="fixed123"), _no_fetch():
        client.post("/shorten", json={"url": "https://example.org/target"})
    r = client.get("/r/fixed123", follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"] == "https://example.org/target"


def test_redirect_unknown_code_returns_404(client: TestClient) -> None:
    r = client.get("/r/doesnotexist", follow_redirects=False)
    assert r.status_code == 404
    assert r.json()["detail"] == "Unknown short code"


def test_shorten_invalid_url_returns_422(client: TestClient) -> None:
    r = client.post("/shorten", json={"url": "not-a-url"})
    assert r.status_code == 422


def test_shorten_retries_on_code_collision(client: TestClient) -> None:
    codes = iter(["dup", "dup", "unique9"])

    def fake_random_code(length: int = 8) -> str:
        return next(codes)

    with patch.object(app_module, "_random_code", side_effect=fake_random_code), _no_fetch():
        r1 = client.post("/shorten", json={"url": "https://a.com/"})
        r2 = client.post("/shorten", json={"url": "https://b.com/"})
    assert r1.status_code == 200
    assert r1.json()["code"] == "dup"
    assert r2.status_code == 200
    assert r2.json()["code"] == "unique9"


@pytest.mark.parametrize("length", [1, 8, 16])
def test_random_code_length_and_charset(length: int) -> None:
    code = _random_code(length)
    assert len(code) == length
    assert code.isalnum()


def test_random_code_uses_secrets_choice() -> None:
    with patch("shortener.app.secrets.choice", side_effect=list("x" * 8)):
        assert _random_code(8) == "xxxxxxxx"


def test_recent_empty_list(client: TestClient) -> None:
    r = client.get("/links/recent")
    assert r.status_code == 200
    assert r.json() == []

def test_recent_limit_param_returns_ten(client: TestClient) -> None:
    with _no_fetch():
        for i in range(12):
            with patch.object(app_module, "_random_code", return_value=f"c{i:02d}"):
                client.post("/shorten", json={"url": f"https://ex.test/{i}"})
    r = client.get("/links/recent", params={"limit": 10})
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 10
    codes = [row["code"] for row in data]
    assert codes[0] == "c11"
    assert codes[-1] == "c02"


def test_recent_returns_last_five_newest_first(client: TestClient) -> None:
    with _no_fetch():
        for i in range(8):
            with patch.object(app_module, "_random_code", return_value=f"c{i:02d}"):
                client.post("/shorten", json={"url": f"https://ex.test/{i}"})
    r = client.get("/links/recent")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 5
    codes = [row["code"] for row in data]
    assert codes == ["c07", "c06", "c05", "c04", "c03"]
    for row in data:
        assert set(row.keys()) == {"name", "code", "url", "created_at"}
        assert row["url"].startswith("https://ex.test/")


def test_search_finds_by_code(client: TestClient) -> None:
    with patch.object(app_module, "_random_code", return_value="findme01"), _no_fetch():
        client.post("/shorten", json={"url": "https://a.com/z"})
    r = client.get("/links/search", params={"q": "findme"})
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) >= 1
    assert any(row["code"] == "findme01" for row in rows)


def test_search_finds_by_title_and_url(client: TestClient) -> None:
    with patch.object(app_module, "_random_code", return_value="s1"), _no_fetch():
        client.post(
            "/shorten",
            json={
                "url": "https://unique-domain.test/path",
                "title": "Unique Banana Title",
            },
        )
    r_title = client.get("/links/search", params={"q": "Banana"})
    assert r_title.status_code == 200
    assert any(r["code"] == "s1" for r in r_title.json())
    r_url = client.get("/links/search", params={"q": "unique-domain"})
    assert r_url.status_code == 200
    assert any(r["code"] == "s1" for r in r_url.json())


def test_search_empty_query_returns_422(client: TestClient) -> None:
    r = client.get("/links/search", params={"q": ""})
    assert r.status_code == 422


def test_create_app_accepts_custom_lifespan() -> None:
    app = create_app(lifespan=_empty_lifespan)
    assert app.title == "URL Shortener"
