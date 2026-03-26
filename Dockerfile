FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --no-cache-dir .

EXPOSE 4320

ENV APP_HOST=0.0.0.0
ENV APP_PORT=4320

CMD ["python", "-m", "shortener"]
