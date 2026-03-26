import os

import uvicorn


def main() -> None:
    # uvicorn bind host/port for the HTTP server.
    # Use APP_* to avoid clashing with DB_* environment variables.
    host = os.environ.get("APP_HOST", os.environ.get("HOST", "0.0.0.0"))
    port = int(os.environ.get("APP_PORT", os.environ.get("PORT", "8000")))
    uvicorn.run(
        "shortener.app:app",
        host=host,
        port=port,
        factory=False,
    )


if __name__ == "__main__":
    main()
