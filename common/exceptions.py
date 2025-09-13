from typing import Any, Dict, Optional
from django.http import Http404
from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework.exceptions import (
    APIException, ValidationError, NotAuthenticated, PermissionDenied, NotFound,
    AuthenticationFailed,
)
from rest_framework.response import Response
from rest_framework import status as S

DEFAULT_ERROR_CODES = {
    "ValidationError":   "VALIDATION_ERROR",
    "NotAuthenticated":  "AUTH_REQUIRED",
    "AuthenticationFailed": "AUTH_INVALID",
    "PermissionDenied":  "FORBIDDEN",
    "NotFound":          "NOT_FOUND",
    "Http404":           "NOT_FOUND",
    "MethodNotAllowed":  "METHOD_NOT_ALLOWED",
    "ParseError":        "BAD_REQUEST",
    "UnsupportedMediaType": "UNSUPPORTED_MEDIA_TYPE",
    "NotAcceptable":     "NOT_ACCEPTABLE",
    "Throttled":         "TOO_MANY_REQUESTS",
}

class AppError(APIException):
    def __init__(self, message: str,
                 status_code: int = S.HTTP_400_BAD_REQUEST,
                 code: Optional[str] = None,
                 extra: Optional[Dict[str, Any]] = None):
        super().__init__(detail=message)
        self.status_code = status_code
        self.app_code = code or "APP_ERROR"
        self.extra = extra or {}

def _err(message: str, http_status: int,
         code: Optional[str] = None,
         extra: Optional[Dict[str, Any]] = None) -> Response:
    payload: Dict[str, Any] = {"message": message, "statusCode": http_status}
    if code:
        payload["code"] = code
    if extra:
        payload["errors"] = extra
    return Response(payload, status=http_status)

def _code_by_status(sc: int) -> str:
    if sc == 400: return "BAD_REQUEST"
    if sc == 401: return "UNAUTHORIZED"
    if sc == 403: return "FORBIDDEN"
    if sc == 404: return "NOT_FOUND"
    if sc == 405: return "METHOD_NOT_ALLOWED"
    if sc == 415: return "UNSUPPORTED_MEDIA_TYPE"
    if sc == 429: return "TOO_MANY_REQUESTS"
    if 500 <= sc < 600: return "INTERNAL_SERVER_ERROR"
    return "ERROR"

def exception_handler(exc, context):

    if isinstance(exc, AppError):
        return _err(str(exc.detail), exc.status_code, exc.app_code, exc.extra or None)


    if isinstance(exc, NotAuthenticated):
        return _err("인증이 필요합니다.", S.HTTP_401_UNAUTHORIZED, "AUTH_REQUIRED")
    if isinstance(exc, AuthenticationFailed):
        return _err("로그인 정보가 유효하지 않습니다.", S.HTTP_401_UNAUTHORIZED, "AUTH_INVALID")
    if isinstance(exc, PermissionDenied):
        return _err("권한이 없습니다.", S.HTTP_403_FORBIDDEN, "FORBIDDEN")
    if isinstance(exc, NotFound):
        return _err("리소스를 찾을 수 없습니다.", S.HTTP_404_NOT_FOUND, "NOT_FOUND")
    if isinstance(exc, Http404):
        return _err("리소스를 찾을 수 없습니다.", S.HTTP_404_NOT_FOUND, "NOT_FOUND")
    if isinstance(exc, ValidationError):
        detail = getattr(exc, "detail", None)
        def first(o):
            if isinstance(o, (list, tuple)) and o: return first(o[0])
            if isinstance(o, dict) and o: return first(next(iter(o.values())))
            return str(o)
        message = first(detail) or "요청 값이 올바르지 않습니다."
        extra = detail if isinstance(detail, (dict, list)) else None
        return _err(message, S.HTTP_400_BAD_REQUEST, "VALIDATION_ERROR", extra)

    resp = drf_exception_handler(exc, context)
    if resp is not None:
        raw = resp.data
        if isinstance(raw, dict):
            msg = raw.get("message") or raw.get("detail") or "오류가 발생했습니다."

            code = DEFAULT_ERROR_CODES.get(exc.__class__.__name__) or _code_by_status(resp.status_code)
            extra = None
            if raw and not raw.get("message") and not raw.get("detail"):
                extra = raw
            return _err(msg, resp.status_code, code, extra)
        return _err(str(raw) if raw else "오류가 발생했습니다.", resp.status_code, _code_by_status(resp.status_code))

    # 4) 마지막 안전망
    return _err("서버 오류가 발생했습니다.", S.HTTP_500_INTERNAL_SERVER_ERROR, "INTERNAL_SERVER_ERROR")
