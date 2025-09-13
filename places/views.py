from typing import Optional

from django.db.models import Prefetch, Case, When, Value, IntegerField, Count
from django.shortcuts import get_object_or_404
from django.contrib.contenttypes.models import ContentType
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from common.exceptions import AppError

from rest_framework.exceptions import ValidationError

from .models import Place, PlaceImage
from .serializers import (
    PlaceMapAllQuery, PlaceDetailQuery, PlaceListQuery, PlaceSearchQuery
)
from .constants import CONTENT_TYPE_LABELS, SIZE_KEYWORDS, AREA_KEYWORDS, AMENITY_KEYWORDS
from .utils import (
    parse_bbox, text_or_unknown, parking_text,
    conditions_text, split_lines, prune_empty,
    haversine_km, address_brief, thumb_or_text, collect_text,
    find_labels, place_type_label, build_filter_q,
    split_terms, and_icontains,
)
from scraps.models import Scrap

def _scrapped_pk_set(user, places):
    if not (user and user.is_authenticated):
        return set()
    pks = [p.pk for p in places]
    if not pks:
        return set()
    ct = ContentType.objects.get_for_model(Place)
    return set(
        Scrap.objects.filter(user=user, content_type=ct, object_id__in=pks)
                     .values_list("object_id", flat=True)
    )


def _scrapped_bool(user, place: Place) -> bool:
    if not (user and user.is_authenticated):
        return False
    ct = ContentType.objects.get_for_model(Place)
    return Scrap.objects.filter(user=user, content_type=ct, object_id=place.pk).exists()

def _scrap_counts_for_places(places) -> dict[int, int]:
    pks = [p.pk for p in places]
    if not pks:
        return {}
    ct = ContentType.objects.get_for_model(Place)
    rows = (
        Scrap.objects
        .filter(content_type=ct, object_id__in=pks)
        .values("object_id")
        .annotate(c=Count("id"))
    )
    return {r["object_id"]: r["c"] for r in rows}

def _scrap_count_for_place(place: Place) -> int:
    ct = ContentType.objects.get_for_model(Place)
    return Scrap.objects.filter(content_type=ct, object_id=place.pk).count()


class PlaceMapAllView(APIView):
    @swagger_auto_schema(
        operation_summary="장소 전체 목록 조회 - 지도",
        operation_description="지도 기반 장소를 전체 조회합니다. contentTypeId로 장소 카테고리를 분류합니다."
                              "12: 관광지 | 14:문화시설 | 15: 축제/공연/행사 | 28: 레포츠 | 32: 숙박 | 38: 쇼핑 |  39: 음식점",
        tags=["Places"],
        query_serializer=PlaceMapAllQuery,
    )
    def get(self, request):
        s = PlaceMapAllQuery(data=request.query_params)
        s.is_valid(raise_exception=True)
        q = s.validated_data

        try:
            min_lng, min_lat, max_lng, max_lat = parse_bbox(q["bbox"])
        except Exception:
            raise AppError("bbox는 'minLng,minLat,maxLng,maxLat' 형식이어야 합니다.",
                           status_code=400, code="BBOX_INVALID")

        base = Place.objects.filter(
            mapx__isnull=False, mapy__isnull=False,
            mapx__gte=min_lng, mapx__lte=max_lng,
            mapy__gte=min_lat, mapy__lte=max_lat,
        )
        if q.get("contentTypeId"):
            base = base.filter(content_type_id=q["contentTypeId"])

        base = base.filter(build_filter_q(q))

        base = (
            base.prefetch_related(Prefetch("images", queryset=PlaceImage.objects.order_by("id")))
                .select_related("pet_policy")
                .order_by("-updated_at")[: q.get("limit", 100)]
        )

        rows = list(base)
        scraped_set = _scrapped_pk_set(request.user, rows)
        scrap_counts = _scrap_counts_for_places(rows)

        items = [{
            "contentId": p.content_id,
            "contentType": {"id": p.content_type_id, "name": CONTENT_TYPE_LABELS.get(p.content_type_id, "기타")},
            "title": p.title,
            "lat": p.mapy,
            "lng": p.mapx,
            "thumbnail": (p.images.first().thumb or p.images.first().origin) if p.images.first() else None,
            "isScrapped": (p.pk in scraped_set),
            "scrapCount": scrap_counts.get(p.pk, 0),
        } for p in rows]

        request._resp_message = "지도용 장소 목록 조회"
        return Response({"total": len(items), "items": items})


class PlaceListView(APIView):
    @swagger_auto_schema(
        operation_summary="장소 전체 목록 조회 - 리스트",
        operation_description="장소 리스트를 전체 조회합니다. contentTypeId로 장소 카테고리를 분류합니다."
                              "12: 관광지 | 14:문화시설 | 15: 축제/공연/행사 | 28: 레포츠 | 32: 숙박 | 38: 쇼핑 |  39: 음식점",
        tags=["Places"],
        query_serializer=PlaceListQuery,
    )
    def get(self, request):
        s = PlaceListQuery(data=request.query_params)
        s.is_valid(raise_exception=True)
        q = s.validated_data

        qs = Place.objects.filter(mapx__isnull=False, mapy__isnull=False)
        if q.get("contentTypeId"):
            qs = qs.filter(content_type_id=q["contentTypeId"])

        qs = qs.filter(build_filter_q(q))

        qs = (qs.select_related("pet_policy")
                .prefetch_related(Prefetch("images", queryset=PlaceImage.objects.order_by("id")))
                .order_by("-updated_at"))

        if not q.get("all"):
            start = q.get("offset", 0)
            end = start + q.get("limit", 50)
            qs = qs[start:end]

        rows = list(qs)
        scraped_set = _scrapped_pk_set(request.user, rows)
        scrap_counts = _scrap_counts_for_places(rows)

        user_lat = q.get("userLat")
        user_lng = q.get("userLng")

        items = []
        for p in rows:
            policy = getattr(p, "pet_policy", None)

            src = collect_text(p)
            sizes = find_labels(src, SIZE_KEYWORDS)
            areas = find_labels(src, AREA_KEYWORDS)
            amens = find_labels(src, AMENITY_KEYWORDS)
            cond = conditions_text(policy)

            chips = []
            if sizes: chips.append(sizes[0])
            if areas: chips.append(areas[0])
            if cond and cond != "정보없음": chips.append(cond)
            if amens: chips.append(amens[0])

            meta_line = f"{address_brief(p.addr1)} · {place_type_label(p) or ''}".rstrip(" ·")

            dist_text = None
            if user_lat is not None and user_lng is not None:
                d = haversine_km(user_lat, user_lng, p.mapy, p.mapx)
                if d is not None:
                    dist_text = f"{d}km"

            items.append({
                "contentId": p.content_id,
                "contentType": {"id": p.content_type_id, "name": CONTENT_TYPE_LABELS.get(p.content_type_id, "기타")},
                "title": p.title,
                "metaLine": meta_line,
                "distanceText": dist_text,
                "thumbnail": thumb_or_text(p),
                "chips": chips,
                "isScrapped": (p.pk in scraped_set),
                "scrapCount": scrap_counts.get(p.pk, 0),
            })

        request._resp_message = "장소 목록 조회"
        return Response({"total": len(items), "items": items})


class PlaceDetailView(APIView):
    @swagger_auto_schema(
        operation_summary="장소 단일 조회",
        operation_description="장소를 단일 조회합니다. 기본 정보 포함.",
        tags=["Places"],
        query_serializer=PlaceDetailQuery,
    )
    def get(self, request, contentId: int):
        s = PlaceDetailQuery(data=request.query_params)
        s.is_valid(raise_exception=True)
        q = s.validated_data

        try:
            p = (Place.objects
                 .prefetch_related(Prefetch("images", queryset=PlaceImage.objects.order_by("id")))
                 .select_related("pet_policy")
                 .get(content_id=contentId))
        except Place.DoesNotExist:
            raise AppError("장소를 찾을 수 없습니다.", status_code=404, code="PLACE_NOT_FOUND")
        policy = getattr(p, "pet_policy", None)

        dist_km: Optional[float] = None
        if "userLat" in q and "userLng" in q:
            dist_km = haversine_km(q["userLat"], q["userLng"], p.mapy, p.mapx)

        data = {
            "contentId": p.content_id,
            "contentType": {"id": p.content_type_id, "name": CONTENT_TYPE_LABELS.get(p.content_type_id, "기타")},
            "title": p.title,
            "address": text_or_unknown(p.addr1),
            "hasParkingText": parking_text(p.has_parking),
            "acmpyTypeCd": text_or_unknown(getattr(policy, "acmpy_type_cd", None)),
            "conditions": conditions_text(policy),
            "thumbnail": thumb_or_text(p),
            "isScrapped": _scrapped_bool(request.user, p),
            "scrapCount": _scrap_count_for_place(p),
        }
        if dist_km is not None:
            data["distanceText"] = f"{dist_km}km"

        request._resp_message = "장소 단일 조회"
        return Response(data)


class PlaceDetailFullView(APIView):
    @swagger_auto_schema(
        operation_summary="장소 상세 조회",
        operation_description="장소를 상세 조회합니다. 기본 정보 + 상세 정보까지 포함.",
        tags=["Places"],
        query_serializer=PlaceDetailQuery,
    )
    def get(self, request, contentId: int):
        s = PlaceDetailQuery(data=request.query_params)
        s.is_valid(raise_exception=True)
        q = s.validated_data

        try:
            p = (Place.objects
                 .prefetch_related(Prefetch("images", queryset=PlaceImage.objects.order_by("id")))
                 .select_related("pet_policy")
                 .get(content_id=contentId))
        except Place.DoesNotExist:
            raise AppError("장소를 찾을 수 없습니다.", status_code=404, code="PLACE_NOT_FOUND")
        policy = getattr(p, "pet_policy", None)

        images = [{"origin": img.origin, "thumb": img.thumb or None} for img in p.images.all()]
        src = collect_text(p)

        chips = {
            "sizes": find_labels(src, SIZE_KEYWORDS),
            "areas": find_labels(src, AREA_KEYWORDS),
            "conditions": conditions_text(policy),
            "amenities": find_labels(src, AMENITY_KEYWORDS),
        }

        data = {
            "title": p.title,
            "address": text_or_unknown(p.addr1),
            "openHours": text_or_unknown(p.usetime),
            "tel": text_or_unknown(p.tel),
            "homepage": text_or_unknown(p.homepage),
            "thumbnail": thumb_or_text(p),
            "images": images,
            "chips": chips,
            "petPolicy": {
                "acmpyTypeCd": text_or_unknown(getattr(policy, "acmpy_type_cd", None)),
                "notes": split_lines(getattr(policy, "etc_info", "")),
            },
            "isScrapped": _scrapped_bool(request.user, p),
            "scrapCount": _scrap_count_for_place(p),
        }

        dist_km: Optional[float] = None
        if "userLat" in q and "userLng" in q:
            dist_km = haversine_km(q["userLat"], q["userLng"], p.mapy, p.mapx)
        if dist_km is not None:
            data["distanceText"] = f"{dist_km}km"

        request._resp_message = "장소 상세 조회"
        return Response(prune_empty(data))


class PlaceSearchView(APIView):
    @swagger_auto_schema(
        operation_summary="장소 검색",
        operation_description="장소를 검색합니다. contentTypeId로 카테고리를 분류합니다."
                              "12: 관광지 | 14:문화시설 | 15: 축제/공연/행사 | 28: 레포츠 | 32: 숙박 | 38: 쇼핑 |  39: 음식점",
        tags=["Places"],
        query_serializer=PlaceSearchQuery,
    )
    def get(self, request):
        s = PlaceSearchQuery(data=request.query_params)
        s.is_valid(raise_exception=True)
        q = s.validated_data

        qs = Place.objects.filter(mapx__isnull=False, mapy__isnull=False)
        if q.get("contentTypeId"):
            qs = qs.filter(content_type_id=q["contentTypeId"])

        terms = split_terms(q["q"])
        if not terms:
            raise AppError("검색어는 2글자 이상으로 입력해 주세요.",
                           status_code=400, code="QUERY_TOO_SHORT")

        qs = qs.filter(and_icontains(["title", "addr1", "overview", "pet_policy__etc_info"], terms))

        score = Value(0, output_field=IntegerField())
        for t in terms:
            score = score + Case(
                When(title__iexact=t,                   then=Value(100)),
                When(title__istartswith=t,              then=Value(90)),
                When(title__icontains=t,                then=Value(80)),
                When(addr1__icontains=t,                then=Value(60)),
                When(overview__icontains=t,             then=Value(20)),
                When(pet_policy__etc_info__icontains=t, then=Value(10)),
                default=Value(0), output_field=IntegerField(),
            )

        qs = (qs.select_related("pet_policy")
                .prefetch_related(Prefetch("images", queryset=PlaceImage.objects.order_by("id")))
                .annotate(score=score)
                .order_by("-score", "-updated_at"))

        if not q.get("all"):
            start = q.get("offset", 0)
            end = start + q.get("limit", 50)
            qs = qs[start:end]

        rows = list(qs)
        scraped_set = _scrapped_pk_set(request.user, rows)
        scrap_counts = _scrap_counts_for_places(rows)

        user_lat = q.get("userLat")
        user_lng = q.get("userLng")

        items = []
        for p in rows:
            policy = getattr(p, "pet_policy", None)

            src = collect_text(p)
            sizes = find_labels(src, SIZE_KEYWORDS)
            areas = find_labels(src, AREA_KEYWORDS)
            amens = find_labels(src, AMENITY_KEYWORDS)
            cond = conditions_text(policy)

            chips_list = []
            if sizes: chips_list.append(sizes[0])
            if areas: chips_list.append(areas[0])
            if cond and cond != "정보없음": chips_list.append(cond)
            if amens: chips_list.append(amens[0])

            chips_value = chips_list[0] if len(chips_list) == 1 else chips_list

            meta_line = f"{address_brief(p.addr1)} · {place_type_label(p) or ''}".rstrip(" ·")

            dist_text = None
            if user_lat is not None and user_lng is not None:
                d = haversine_km(user_lat, user_lng, p.mapy, p.mapx)
                if d is not None:
                    dist_text = f"{d}km"

            item = {
                "contentId": p.content_id,
                "contentType": {"id": p.content_type_id, "name": CONTENT_TYPE_LABELS.get(p.content_type_id, "기타")},
                "title": p.title,
                "metaLine": meta_line,
                "distanceText": dist_text,
                "thumbnail": thumb_or_text(p),
                "chips": chips_value,
                "isScrapped": (p.pk in scraped_set),
                "scrapCount": _scrap_count_for_place(p),
            }
            items.append(prune_empty(item))

        request._resp_message = "장소 검색 결과"
        return Response({"total": len(items), "items": items})
