from __future__ import annotations

import secrets
import string
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, AsyncIterator

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, HttpUrl
from sqlalchemy import Select, or_, select
from sqlalchemy.orm import Session

from shortener.db import get_db, init_db
from shortener.models import ShortLink
from shortener.title_fetch import fetch_page_title

_STATIC_DIR = Path(__file__).resolve().parent / "static"
_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
_templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

_alphabet = string.ascii_letters + string.digits


def _random_code(length: int = 8) -> str:
    return "".join(secrets.choice(_alphabet) for _ in range(length))


class ShortenBody(BaseModel):
    url: HttpUrl
    title: str | None = None


@asynccontextmanager
async def default_lifespan(_: FastAPI) -> AsyncIterator[None]:
    init_db()
    yield


def create_app(*, lifespan=default_lifespan) -> FastAPI:
    app = FastAPI(title="URL Shortener", version="0.1.0", lifespan=lifespan)

    if _STATIC_DIR.is_dir():
        app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

    def _link_item(row: ShortLink) -> dict[str, str | None]:
        created = row.created_at
        if hasattr(created, "isoformat"):
            created_str = created.isoformat()
        else:
            created_str = str(created)
        return {
            "name": row.title,
            "code": row.code,
            "url": row.url,
            "created_at": created_str,
        }

    @app.get("/")
    def index(request: Request):
        return _templates.TemplateResponse(
            request=request,
            name="index.html",
        )

    @app.post("/shorten")
    @app.post("/shorten/")
    def shorten(
        body: ShortenBody,
        db: Annotated[Session, Depends(get_db)],
    ) -> dict[str, str | None]:
        url_str = str(body.url)
        page_title = body.title
        if page_title is None:
            page_title = fetch_page_title(url_str)

        while True:
            code = _random_code()
            exists = db.scalar(select(ShortLink.code).where(ShortLink.code == code))
            if exists is None:
                break

        row = ShortLink(code=code, url=url_str, title=page_title)
        db.add(row)
        db.commit()
        return {"code": code, "path": f"/r/{code}", "title": page_title}

    @app.get("/r/{code}")
    def redirect(
        code: str,
        db: Annotated[Session, Depends(get_db)],
    ) -> RedirectResponse:
        row = db.get(ShortLink, code)
        if row is None:
            raise HTTPException(status_code=404, detail="Unknown short code")
        return RedirectResponse(row.url, status_code=302)

    @app.get("/links/recent")
    def recent_links(
        db: Annotated[Session, Depends(get_db)],
        limit: Annotated[int, Query(ge=1, le=10)] = 5,
    ) -> list[dict[str, str | None]]:
        stmt: Select[tuple[ShortLink]] = (
            select(ShortLink)
            .order_by(ShortLink.created_at.desc(), ShortLink.code.desc())
            .limit(limit)
        )
        rows = db.scalars(stmt).all()
        return [_link_item(r) for r in rows]

    @app.get("/links/search")
    def search_links(
        db: Annotated[Session, Depends(get_db)],
        q: Annotated[str, Query(min_length=1)],
        limit: Annotated[int, Query(ge=1, le=100)] = 50,
    ) -> list[dict[str, str | None]]:
        pattern = f"%{q.strip()}%"
        stmt = (
            select(ShortLink)
            .where(
                or_(
                    ShortLink.code.ilike(pattern),
                    ShortLink.url.ilike(pattern),
                    ShortLink.title.ilike(pattern),
                )
            )
            .order_by(ShortLink.created_at.desc(), ShortLink.code.desc())
            .limit(limit)
        )
        rows = db.scalars(stmt).all()
        return [_link_item(r) for r in rows]

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
