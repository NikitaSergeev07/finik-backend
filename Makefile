.PHONY: dev migrate revision test lint
dev:        ## запустить API с автоперезагрузкой
	uv run uvicorn --app-dir src main:app --reload --port 8000
migrate:    ## применить миграции
	uv run alembic upgrade head
revision:   ## создать миграцию по моделям: make revision m="описание"
	uv run alembic revision --autogenerate -m "$(m)"
test:
	FINIK_DATABASE_URL=postgresql+asyncpg://localhost:5432/finik_test uv run pytest -q
seed:       ## заполнить справочники контентом
	PYTHONPATH=src uv run python -m infrastructure.content.seed
lint:
	uv run ruff check src tests && uv run ruff format --check src tests
