FROM python:3.10-slim

RUN apt-get update && apt-get install -y python3-poetry

COPY pyproject.toml poetry.lock ./

RUN poetry install --no-root --with telegram

COPY . .

RUN poetry run python -m sp_tg
