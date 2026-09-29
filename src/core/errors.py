"""Ошибки приложения. Домен бросает свои исключения, API переводит их в HTTP-ответы."""


class AppError(Exception):
    """Базовая ошибка с кодом для клиента и человекочитаемым сообщением по-русски."""

    code = "app_error"
    status_code = 400

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        if code:
            self.code = code


class NotFound(AppError):
    code = "not_found"
    status_code = 404


class Conflict(AppError):
    code = "conflict"
    status_code = 409


class Unauthorized(AppError):
    code = "unauthorized"
    status_code = 401


class Forbidden(AppError):
    code = "forbidden"
    status_code = 403


class RuleViolation(AppError):
    """Действие противоречит правилам игры: нет монет в статье, план больше дохода и т.п."""

    code = "rule_violation"
    status_code = 422
