"""Точка входа. Собирает приложение, вешает обработчик ошибок домена."""

from fastapi import FastAPI, Request
from fastapi.responses import ORJSONResponse

from finik.api.router import api_router
from finik.core.config import get_settings
from finik.core.errors import AppError


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Финик API",
        version="0.1.0",
        description="Серверная часть детского приложения по финансовой грамотности.",
        default_response_class=ORJSONResponse,
        docs_url="/docs" if settings.debug else None,
    )
    app.include_router(api_router)

    @app.exception_handler(AppError)
    async def app_error_handler(_: Request, exc: AppError) -> ORJSONResponse:
        return ORJSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.get("/health", tags=["Служебное"], summary="Проверка живости")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
