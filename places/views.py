from typing import Tuple, List
from functools import reduce
from operator import or_

from django.db.models import Prefetch, Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema

from .serializers import PlaceMapAllQuery
from .models import Place, PlaceImage


def _parse_bbox(bbox_str: str) -> Tuple[float, float, float, float]:
    parts = [p.strip() for p in bbox_str.split(",")]
    if len(parts) != 4:
        raise ValueError
    min_lng, min_lat, max_lng, max_lat = map(float, parts)
    return min_lng, min_lat, max_lng, max_lat


def _or_icontains(fields: List[str], terms: List[str]) -> Q:
    """여러 필드/키워드를 OR로 묶는 헬퍼"""
    terms = [t for t in terms if t]
    if not fields or not terms:
        return Q()
    qs = []
    for f in fields:
        for t in terms:
            qs.append(Q(**{f"{f}__icontains": t}))
    return reduce(or_, qs) if qs else Q()


class PlaceMapAllView(APIView):

    @swagger_auto_schema(
        operation_summary="장소 전체 목록 조회 - 지도",
        tags=["Places"],
        query_serializer=PlaceMapAllQuery,
    )
    def get(self, request):
        ser = PlaceMapAllQuery(data=request.query_params)
        ser.is_valid(raise_exception=True)
        q = ser.validated_data


        try:
            min_lng, min_lat, max_lng, max_lat = _parse_bbox(q["bbox"])
        except Exception:
            return Response(
                {"detail": "bbox must be 'minLng,minLat,maxLng,maxLat' format"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        qs = (
            Place.objects.filter(
                mapx__isnull=False, mapy__isnull=False,
                mapx__gte=min_lng, mapx__lte=max_lng,
                mapy__gte=min_lat, mapy__lte=max_lat,
            )
        )

        ctype = q.get("contentTypeId")
        if ctype:
            qs = qs.filter(content_type_id=ctype)


        sizes = set(q.get("sizes") or [])
        if sizes and "all" not in sizes:
            size_code_map = {"small": "01", "med": "02", "large": "03", "xlarge": "04"}
            size_codes = [size_code_map[s] for s in sizes if s in size_code_map]

            size_q = Q()
            for code in size_codes:
                size_q |= Q(pet_policy__acmpy_type_cd__icontains=code)


            size_text = []
            if "small" in sizes:  size_text += ["소형", "10kg 미만"]
            if "med" in sizes:    size_text += ["중형", "10~24", "10-24"]
            if "large" in sizes:  size_text += ["대형", "25~44", "25-44"]
            if "xlarge" in sizes: size_text += ["초대형", "45kg", "초대"]
            size_q |= _or_icontains(["pet_policy__etc_info", "overview"], size_text)

            if size_q:
                qs = qs.filter(size_q)

        # 4-2) 출입 가능 장소
        areas = set(q.get("areas") or [])
        if areas:
            area_terms = []
            if "indoor" in areas:   area_terms += ["실내", "인도어"]
            if "outdoor" in areas:  area_terms += ["야외", "실외", "아웃도어"]
            if "allarea" in areas:  area_terms += ["전 구역", "전체 구역", "모든 구역"]
            if area_terms:
                qs = qs.filter(_or_icontains(["pet_policy__etc_info", "overview"], area_terms))

        # 4-3) 출입 조건
        conds = set(q.get("conditions") or [])
        if conds:
            cond_terms = []
            if "leash" in conds:        cond_terms += ["목줄 착용", "리드줄 착용", "리드줄 필수"]
            if "carrier" in conds:      cond_terms += ["이동 가방", "캐리어", "케이지"]
            if "leash_free" in conds:   cond_terms += ["목줄 자유", "노리드", "프리"]
            if "diaper" in conds:       cond_terms += ["기저귀"]
            if cond_terms:
                qs = qs.filter(_or_icontains(["pet_policy__etc_info", "overview"], cond_terms))

        # 4-4) 편의
        amens = set(q.get("amenities") or [])
        if amens:
            amen_q = Q()

            if "parking" in amens:
                amen_q &= Q(has_parking=True)

            amen_terms = []
            if "bbq" in amens:        amen_terms += ["바베큐", "바비큐", "BBQ"]
            if "wifi" in amens:       amen_terms += ["무선인터넷", "와이파이", "Wi-Fi", "WIFI"]
            if "takeout" in amens:    amen_terms += ["테이크아웃", "포장 가능"]
            if "yard" in amens:       amen_terms += ["마당", "잔디마당", "야외 정원"]
            if "pets_zone" in amens:  amen_terms += ["애견 전용", "반려견 전용"]
            if "barking_ok" in amens: amen_terms += ["짖음 OK", "짖어도", "소음 허용"]
            if "jacuzzi" in amens:    amen_terms += ["자쿠지", "제쿠지", "월풀"]

            if amen_terms:
                amen_q &= _or_icontains(["overview", "pet_policy__etc_info"], amen_terms)

            if amen_q:
                qs = qs.filter(amen_q)

        qs = (
            qs.prefetch_related(Prefetch("images", queryset=PlaceImage.objects.order_by("id")))
              .select_related("pet_policy")
              .order_by("-updated_at")[: q["limit"]]
        )

        def _thumb(p: Place):
            im = p.images.first()
            return (im.thumb or im.origin) if im else None

        items = [{
            "contentId": p.content_id,
            "contentTypeId": p.content_type_id,
            "title": p.title,
            "lat": p.mapy,
            "lng": p.mapx,
            "thumbnail": _thumb(p),
        } for p in qs]

        return Response({"total": len(items), "items": items})
