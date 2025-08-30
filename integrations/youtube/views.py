from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema

from .serializers import YouTubeSyncRequest
from daenggle.service.ingest import sync_keywords

class YouTubeSyncView(APIView):

    @swagger_auto_schema(operation_summary="YouTube 키워드 수집 실행(저장까지)", tags=["Integration/YouTube"],
                         request_body=YouTubeSyncRequest)
    def post(self, request):
        ser = YouTubeSyncRequest(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        result = sync_keywords(
            d["keywords"],
            days=d["days"],
            pages=d["pages"],
            max_duration_seconds=d["maxDuration"],
            category=d["category"],
            context_id=d.get("contextId", ""),
            context_name=d.get("contextName", ""),
        )
        return Response({**result,
                         "limits": {"days": d["days"], "pages": d["pages"], "maxDuration": d["maxDuration"]}},
                        status=status.HTTP_200_OK)
