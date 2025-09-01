import secrets
from urllib.parse import urlencode
from django.conf import settings
from django.shortcuts import redirect

from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from drf_yasg.utils import swagger_auto_schema

class KakaoLoginStartView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="카카오 로그인 시작",
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
