from rest_framework.views import APIView
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema

from daenggle.serializers import ShortsQuery
from daenggle.service.query import list_shorts

class ShortsListView(APIView):
    @swagger_auto_schema(operation_summary="섹션별 댕글 영상 조회",
                         operation_description="섹션(장소/숙소/트렌드)별 댕글 영상 목록을 조회합니다.",
                         tags=["Daenggle"],
                         query_serializer=ShortsQuery)
    def get(self, request):
        s = ShortsQuery(data=request.query_params)
        s.is_valid(raise_exception=True)
        q = s.validated_data

        if q["type"] == "keyword" and not q.get("keyword"):
            return Response({"detail": "keyword is required for type=keyword"}, status=400)

        res = list_shorts(
            q["type"],
            context_id=q.get("contextId") or None,
            keyword=q.get("keyword") or None,
            days=q.get("days"),
            max_duration=q.get("maxDuration"),
            limit=q["limit"],
            offset=q["offset"],
            sort=q["sort"],
        )
        return Response(res)
