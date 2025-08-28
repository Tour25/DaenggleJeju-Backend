from rest_framework.views import APIView
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .client import KTOClient, items_as_list
from .serializers import (AreaBasedListQuery,LocationBasedListQuery,SearchKeywordQuery,PetTourSyncQuery,EnrichIdsBody,)
from .sync import (sync_area_and_sigungu, sync_category,upsert_place_from_list,enrich_detail,run_incremental,run_bootstrap_area,)
from places.models import AreaCode

cli = KTOClient()

class AreaCodeView(APIView):
    @swagger_auto_schema(operation_summary="지역 코드 동기화 (제주 39만)", tags=["KTO"])
    def post(self, request):

        try:
            areas = items_as_list(cli.get("areaCode", pageNo=1, numOfRows=100))
            jeju_name = next((a.get("name") for a in areas if a.get("code") == "39"), "제주")
        except Exception:
            jeju_name = "제주"


        AreaCode.objects.update_or_create(
            area_code="39", sigungu_code=None, defaults={"name": jeju_name}
        )


        sub = cli.get("areaCode", areaCode="39", pageNo=1, numOfRows=200)
        for s in items_as_list(sub):
            AreaCode.objects.update_or_create(
                area_code="39", sigungu_code=s.get("code"), defaults={"name": s.get("name")}
            )
        return Response({"status": "ok", "areaCode": "39"})

class CategoryCodeView(APIView):
    @swagger_auto_schema(operation_summary="카테고리 코드 동기화", tags=["KTO"])
    def post(self, request):
        sync_category(cli)
        return Response({"status": "ok"})


class AreaBasedListView(APIView):
    @swagger_auto_schema(operation_summary="지역기반 목록 조회", tags=["KTO"], query_serializer=AreaBasedListQuery)
    def get(self, request):
        ser = AreaBasedListQuery(data=request.query_params); ser.is_valid(raise_exception=True)
        body = cli.get("areaBasedList", **ser.validated_data)
        return Response(body)

class LocationBasedListView(APIView):
    @swagger_auto_schema(operation_summary="좌표기반 목록 조회", tags=["KTO"], query_serializer=LocationBasedListQuery)
    def get(self, request):
        ser = LocationBasedListQuery(data=request.query_params); ser.is_valid(raise_exception=True)
        body = cli.get("locationBasedList", **ser.validated_data)
        return Response(body)

class SearchKeywordView(APIView):
    @swagger_auto_schema(operation_summary="키워드 검색 목록 조회", tags=["KTO"], query_serializer=SearchKeywordQuery)
    def get(self, request):
        ser = SearchKeywordQuery(data=request.query_params); ser.is_valid(raise_exception=True)
        body = cli.get("searchKeyword", **ser.validated_data)
        return Response(body)

class DetailPreviewView(APIView):
    @swagger_auto_schema(
        operation_summary="상세 미리보기",
        tags=["KTO"],
        manual_parameters=[
            openapi.Parameter("contentId", openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=True),
            openapi.Parameter("contentTypeId", openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=False),
        ],
    )
    def get(self, request):
        cid_q = request.query_params.get("contentId")
        if not cid_q:
            return Response({"detail": "contentId required"}, status=400)
        cid = int(cid_q)
        ctid = int(request.query_params.get("contentTypeId")) if request.query_params.get("contentTypeId") else None

        common = cli.get("detailCommon", contentId=cid, defaultYN="Y", addrinfoYN="Y", mapinfoYN="Y", overviewYN="Y")
        common_item = (common.get("items", {}) or {}).get("item")
        if ctid is None and isinstance(common_item, dict) and common_item.get("contenttypeid"):
            try:
                ctid = int(common_item["contenttypeid"])
            except (TypeError, ValueError):
                ctid = None

        intro = cli.get("detailIntro", contentId=cid, contentTypeId=ctid) if ctid else {"items": {}}
        info  = cli.get("detailInfo",  contentId=cid, contentTypeId=ctid) if ctid else {"items": {}}
        image = cli.get("detailImage", contentId=cid, numOfRows=50, pageNo=1)
        pet   = cli.get("detailPetTour", contentId=cid)
        return Response({"common": common, "intro": intro, "info": info, "image": image, "pet": pet})


class DailySyncView(APIView):
    @swagger_auto_schema(operation_summary="증분 동기화 실행 (일괄 저장)", tags=["KTO"], request_body=PetTourSyncQuery)
    def post(self, request):
        ser = PetTourSyncQuery(data=request.data); ser.is_valid(raise_exception=True)
        q = ser.validated_data
        if q.get("dry_run"):
            page, total = q["pageNo"], 0
            while True:
                body = cli.get("petTourSyncList", modifiedtime=q["modifiedtime"], showflag=q["showflag"],
                               pageNo=page, numOfRows=q["numOfRows"], listYN="Y", arrange="C")
                items = items_as_list(body)
                if not items: break
                total += len(items)
                if len(items) < q["numOfRows"]: break
                page += 1
            return Response({"dry_run": True, "count": total})
        processed = run_incremental(cli, q["modifiedtime"], q["showflag"], q["numOfRows"])
        return Response({"dry_run": False, "processed": processed})

class BootstrapAreaView(APIView):
    @swagger_auto_schema(
        operation_summary="제주 지역/시군구 전체 수집 + 상세 저장",
        tags=["KTO"]
    )
    def post(self, request):

        done = run_bootstrap_area(
            cli,
            area_code="39",
            sigungu_code="",
            num_rows=100,   # 필요시 조정
            max_pages=999,  # 필요시 조정
        )
        return Response({"processed": done, "areaCode": "39"})

class EnrichIdsView(APIView):
    @swagger_auto_schema(operation_summary="특정 contentId 배열 상세 병합 저장", tags=["KTO"], request_body=EnrichIdsBody)
    def post(self, request):
        ser = EnrichIdsBody(data=request.data); ser.is_valid(raise_exception=True)
        cids = ser.validated_data["ids"]
        for cid in cids:
            enrich_detail(cli, int(cid))
        return Response({"processed": len(cids)})
