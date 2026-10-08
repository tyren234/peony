from typing import Any, List, Optional
from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

# Kompatybilność z nowym nazewnictwem kodów w Starlette / RFC 9110
HTTP_422_STATUS = getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422)

DEFAULT_TITLES = {
    400: "Bad Request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not Found",
    405: "Method Not Allowed",
    406: "Not Acceptable",
    409: "Conflict",
    415: "Unsupported Media Type",
    422: "Unprocessable Entity",
    500: "Internal Server Error",
}


class ProblemException(Exception):
    """Wyjątek rzucany w logice aplikacji, automatycznie mapowany na RFC 9457."""

    def __init__(
        self,
        status_code: Optional[int] = None,
        title: Optional[str] = None,
        detail: Optional[str] = None,
        errors: Optional[List[dict[str, str]]] = None,
        type_: str = "about:blank",
        headers: Optional[dict[str, str]] = None,
        status: Optional[int] = None,
    ):
        self.status_code = status_code if status_code is not None else (status or 500)
        self.title = title or DEFAULT_TITLES.get(self.status_code, "Error")
        self.detail = detail
        self.errors = errors
        self.type_ = type_
        self.headers = headers or {}


def create_problem_response(
    status_code: int,
    title: Optional[str] = None,
    detail: Optional[str] = None,
    instance: Optional[str] = None,
    errors: Optional[List[dict[str, str]]] = None,
    type_: str = "about:blank",
    headers: Optional[dict[str, str]] = None,
) -> JSONResponse:
    """Tworzy obiekt JSONResponse zgodny ze standardem RFC 9457."""
    content: dict[str, Any] = {
        "type": type_,
        "title": title or DEFAULT_TITLES.get(status_code, "Error"),
        "status": status_code,
    }
    if detail is not None:
        content["detail"] = detail
    if instance is not None:
        content["instance"] = instance
    if errors:
        content["errors"] = errors

    response_headers = {
        "Content-Type": "application/problem+json",
        **(headers or {}),
    }
    return JSONResponse(
        status_code=status_code,
        content=content,
        headers=response_headers,
        media_type="application/problem+json",
    )


async def problem_exception_handler(request: Request, exc: ProblemException) -> JSONResponse:
    return create_problem_response(
        status_code=exc.status_code,
        title=exc.title,
        detail=exc.detail,
        instance=request.url.path,
        errors=exc.errors,
        type_=exc.type_,
        headers=exc.headers,
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    return create_problem_response(
        status_code=exc.status_code,
        title=DEFAULT_TITLES.get(exc.status_code, "Error"),
        detail=str(exc.detail) if exc.detail else None,
        instance=request.url.path,
        headers=exc.headers,
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = []
    is_syntax_or_query_error = False

    for err in exc.errors():
        loc = err.get("loc", ())
        err_type = err.get("type", "")

        # Zapytania z błędami w parametrach query/path lub uszkodzonym JSON-ie to 400 Bad Request
        if (len(loc) > 0 and loc[0] in ("query", "path")) or err_type == "json_invalid":
            is_syntax_or_query_error = True

        field_parts = [str(location_item) for location_item in loc if location_item not in ("body",)]
        field_name = ".".join(field_parts) if field_parts else "body"
        errors.append({
            "field": field_name,
            "message": err.get("msg", "Invalid value"),
        })

    status_code = (
        status.HTTP_400_BAD_REQUEST
        if is_syntax_or_query_error
        else HTTP_422_STATUS
    )
    detail = (
        "Invalid request syntax or query parameters."
        if is_syntax_or_query_error
        else "Input validation error."
    )

    return create_problem_response(
        status_code=status_code,
        title=DEFAULT_TITLES.get(status_code, "Validation Error"),
        detail=detail,
        instance=request.url.path,
        errors=errors,
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Obsługuje nieoczekiwane błędy 500 bez ujawniania stacktrace w odpowiedzi."""
    return create_problem_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        title="Internal Server Error",
        detail="An unexpected internal server error occurred.",
        instance=request.url.path,
    )
