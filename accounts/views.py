import secrets
import requests

from urllib.parse import urlencode
from django.conf import settings
from drf_yasg import openapi
from django.contrib.auth import get_user_model, login, logout
from django.db import transaction
from django.shortcuts import redirect
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from .models import SocialAccount
from rest_framework.permissions import IsAuthenticated
import uuid


User = get_user_model()

DEV_HANDLE = "dev"

code_param  = openapi.Parameter("code",  openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False)
state_param = openapi.Parameter("state", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False)
err_param   = openapi.Parameter("error", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False)
err_desc    = openapi.Parameter("error_description", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False)


class KakaoLoginStartView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="카카오 로그인",
        operation_description="Kakao authorize로 302 리다이렉트합니다.",
        tags=["Auth"],
        responses={302: "Redirect to Kakao authorize"},
        security=[],
    )
    def get(self, request):
        state = secrets.token_urlsafe(16)
        request.session["kakao_oauth_state"] = state
        params = {
            "client_id": settings.KAKAO_REST_API_KEY,
            "redirect_uri": settings.KAKAO_REDIRECT_URI,
            "response_type": "code",
            "state": state,
        }
        return redirect(f"https://kauth.kakao.com/oauth/authorize?{urlencode(params)}")


class KakaoCallbackView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="카카오 로그인 콜백",
        operation_description="브라우저가 카카오 로그인/동의를 마친 뒤 리디렉트되는 콜백 URL입니다."
                              "ccode/state 검증 → 토큰 교환 → /v2/user/me 조회 → 세션 로그인 → FRONTEND_CALLBACK_URL로 302 리다이렉트 (?isNew=1|0).",
        manual_parameters=[code_param, state_param, err_param, err_desc],
        tags=["Auth"],
        responses={302: "Redirect to / or /onboarding", 400: "Bad Request"},
        security=[],
    )
    def get(self, request):

        if request.GET.get("error"):
            return Response({"detail": request.GET.get("error_description", "kakao error")}, status=400)

        state = request.GET.get("state")
        saved = request.session.get("kakao_oauth_state")
        if not state or not saved or state != saved:
            return Response({"detail": "invalid state"}, status=400)
        request.session.pop("kakao_oauth_state", None)

        code = request.GET.get("code")
        if not code:
            return Response({"detail": "missing code"}, status=400)

        data = {
            "grant_type": "authorization_code",
            "client_id": settings.KAKAO_REST_API_KEY,
            "redirect_uri": settings.KAKAO_REDIRECT_URI,
            "code": code,
        }
        cs = getattr(settings, "KAKAO_CLIENT_SECRET", "")
        if cs:
            data["client_secret"] = cs

        try:
            token_res = requests.post(
                "https://kauth.kakao.com/oauth/token",
                headers={"Content-Type": "application/x-www-form-urlencoded;charset=utf-8"},
                data=data,
                timeout=5,
            )
            token_res.raise_for_status()
            access_token = token_res.json()["access_token"]
        except Exception as e:
            return Response({"detail": f"token exchange failed: {e}"}, status=400)

        try:
            me_res = requests.get(
                "https://kapi.kakao.com/v2/user/me",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=5,
            )
            me_res.raise_for_status()
            kakao_id = str(me_res.json()["id"])
        except Exception as e:
            return Response({"detail": f"user info failed: {e}"}, status=400)

        is_new = False
        with transaction.atomic():
            link = (SocialAccount.objects
                    .select_related("user")
                    .filter(provider="kakao", provider_user_id=kakao_id)
                    .first())
            if link:
                user = link.user
            else:
                user, created = User.objects.get_or_create(
                    handle=f"kakao_{kakao_id}",
                )
                if created:
                    user.set_unusable_password()
                    user.save()
                SocialAccount.objects.get_or_create(
                    user=user, provider="kakao", provider_user_id=kakao_id
                )
                is_new = created

        login(request, user)
        params = {"isNew": "1" if is_new else "0"}
        return redirect(f"{settings.FRONTEND_CALLBACK_URL}?{urlencode(params)}")

class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(operation_summary="현재 로그인 된 사용자 조회",
                         operation_description="현재 로그인 된 사용자를 조회합니다.",
                         tags=["Auth"] )
    def get(self, request):
        handle = getattr(request.user, "handle", getattr(request.user, "username", None))
        return Response({"id": request.user.id, "handle": handle})


class DevLoginView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="DEV 로그인 - 테스트용",
        operation_description="서버 테스트용 로그인입니다.",
        tags=["Auth/Dev"],
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "userId": openapi.Schema(type=openapi.TYPE_INTEGER),
                    "handle": openapi.Schema(type=openapi.TYPE_STRING),
                },
            )
        },
    )
    def post(self, request):
        if not settings.DEBUG:
            return Response({"detail": "Not available in production."}, status=404)

        User = get_user_model()
        user, _ = User.objects.get_or_create(
            handle=DEV_HANDLE,
            defaults={"is_active": True}
        )
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        return Response({"userId": user.id, "handle": user.handle}, status=200)


class DevLogoutView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="DEV 로그아웃 - 테스트용",
        operation_description="서버 테스트용 로그아웃입니다.",
        tags=["Auth/Dev"],
        request_body=None,
        responses={204: "No Content"},
    )
    def post(self, request):
        logout(request)
        return Response(status=204)