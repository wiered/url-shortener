from shortener.title_fetch import _extract_title, fetch_page_title


def test_extract_title_basic() -> None:
    html = "<html><head><title>Hello &amp; World</title></head></html>"
    assert _extract_title(html) == "Hello & World"


def test_extract_title_multiline() -> None:
    html = "<title>\n  Foo Bar  \n</title>"
    assert _extract_title(html) == "Foo Bar"


def test_extract_title_missing() -> None:
    assert _extract_title("<html></html>") is None


def test_fetch_page_title_httpx_error_returns_none() -> None:
    assert fetch_page_title("http://127.0.0.1:9/__no_such_port__/") is None
