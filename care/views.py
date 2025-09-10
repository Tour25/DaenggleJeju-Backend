from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema

from .content import get_script
from .serializers import (ScriptQuerySerializer,MessageResponseSerializer,AskBodySerializer, AskResponseSerializer)
from .gpt import ask_gpt

def _normalize_text(s: str) -> str:
    return (
        s.replace("\r\n", "\n").replace("\r", "\n")
         .replace("\u2028", "\n").replace("\u2029", "\n")
         .replace("\xa0", " ")
    )

class ScriptView(APIView):
    @swagger_auto_schema(
        operation_summary="AI 여행케어 - 토픽별 스크립트",
        tags=["Care"],
        query_serializer=ScriptQuerySerializer,
        responses={200: MessageResponseSerializer, 400: "bad request", 404: "not found"},
    )
    def get(self, request):
        qs = ScriptQuerySerializer(data=request.query_params)
        qs.is_valid(raise_exception=True)
        topic  = qs.validated_data["topic"]
        option = qs.validated_data["option"]

        try:
            md = get_script(topic, option)
        except KeyError:
            return Response({"detail": "unknown topic/option"}, status=404)

        md = _normalize_text(md)  # 옵션
        return Response({"message": {"type": "script", "markdown": md}}, status=status.HTTP_200_OK)


class AskView(APIView):
    @swagger_auto_schema(
        operation_summary="AI 여행케어 - 자유 질문",
        tags=["Care"],
        request_body=AskBodySerializer,
        responses={200: AskResponseSerializer, 400: "bad request"},
    )
    def post(self, request):
        body = AskBodySerializer(data=request.data)
        body.is_valid(raise_exception=True)

        q = body.validated_data["question"]

        try:
            answer = ask_gpt(q)
        except Exception:
            return Response({"detail": "LLM 호출 실패"}, status=502)

        return Response({"message": {"type": "answer", "markdown": answer}}, status=status.HTTP_200_OK)