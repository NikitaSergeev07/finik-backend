TEST_DATABASE_URL ?= postgresql+asyncpg://localhost:5432/finik_test

.PHONY: dev migrate revision test lint
dev:        ## запустить API с автоперезагрузкой
	uv run uvicorn --app-dir src main:app --reload --port 8000
migrate:    ## применить миграции
	uv run alembic upgrade head
revision:   ## создать миграцию по моделям: make revision m="описание"
	uv run alembic revision --autogenerate -m "$(m)"
test:
	FINIK_DATABASE_URL="$(TEST_DATABASE_URL)" uv run pytest -q
seed:       ## заполнить справочники контентом
	PYTHONPATH=src uv run python -m infrastructure.content.seed
ai-check:   ## проверить ключ GigaChat из .env
	PYTHONPATH=src uv run python -m infrastructure.ai.check
lint:
	uv run ruff check src tests && uv run ruff format --check src tests
