from typing import Optional

from django.db.models import Prefetch, Q
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema

from .models import Place, PlaceImage
from .serializers import PlaceMapAllQuery, PlaceDetailQuery, PlaceListQuery
from .constants import CONTENT_TYPE_LABELS, SIZE_KEYWORDS, AREA_KEYWORDS, AMENITY_KEYWORDS
from .utils import (NO_IMAGE_TEXT,
    parse_bbox, or_icontains, text_or_unknown, parking_text,
    extract_conditions, conditions_text, split_lines, prune_empty,
    haversine_km, address_brief, thumb_or_text, collect_text,
    find_labels, place_type_label, build_filter_q,
)

class PlaceMapAllView(APIView):
    @swagger_auto_schema(
        operation_summary="장소 전체 목록 조회 - 지도",
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
            return Response(
                {"detail": "bbox must be 'minLng,minLat,maxLng,maxLat' format"},
                status=status.HTTP_400_BAD_REQUEST,
            )

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

        items = [{
            "contentId": p.content_id,
            "contentType": {"id": p.content_type_id, "name": CONTENT_TYPE_LABELS.get(p.content_type_id, "기타")},
            "title": p.title,
            "lat": p.mapy,
            "lng": p.mapx,
            "thumbnail": (p.images.first().thumb or p.images.first().origin) if p.images.first() else None,
        } for p in base]

        return Response({"total": len(items), "items": items})


class PlaceListView(APIView):
    @swagger_auto_schema(
        operation_summary="장소 전체 목록 조회 - 리스트",
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

        qs = qs.select_related("pet_policy").prefetch_related(
            Prefetch("images", queryset=PlaceImage.objects.order_by("id"))
        ).order_by("-updated_at")

        if not q.get("all"):
            start = q.get("offset", 0)
            end = start + q.get("limit", 50)
            qs = qs[start:end]

        user_lat = q.get("userLat")
        user_lng = q.get("userLng")

        items = []
        for p in qs:
            policy = getattr(p, "pet_policy", None)

            src = collect_text(p)
            sizes = find_labels(src, SIZE_KEYWORDS)
            areas = find_labels(src, AREA_KEYWORDS)
            amens = find_labels(src, AMENITY_KEYWORDS)
            cond  = conditions_text(policy)

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
            })

        return Response({"total": len(items), "items": items})


class PlaceDetailView(APIView):
    @swagger_auto_schema(
        operation_summary="장소 단일 조회",
        tags=["Places"],
        query_serializer=PlaceDetailQuery,
    )
    def get(self, request, contentId: int):
        s = PlaceDetailQuery(data=request.query_params)
        s.is_valid(raise_exception=True)
        q = s.validated_data

        p = get_object_or_404(
            Place.objects.prefetch_related(Prefetch("images", queryset=PlaceImage.objects.order_by("id")))
                         .select_related("pet_policy"),
            content_id=contentId,
        )
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
        }
        if dist_km is not None:
            data["distanceText"] = f"{dist_km}km"

        return Response(data)


class PlaceDetailFullView(APIView):
    @swagger_auto_schema(
        operation_summary="장소 상세 조회(풀 데이터)",
        tags=["Places"],
        query_serializer=PlaceDetailQuery,
    )
    def get(self, request, contentId: int):
        s = PlaceDetailQuery(data=request.query_params)
        s.is_valid(raise_exception=True)
        q = s.validated_data

        p = get_object_or_404(
            Place.objects.prefetch_related(Prefetch("images", queryset=PlaceImage.objects.order_by("id")))
                         .select_related("pet_policy"),
            content_id=contentId,
        )
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
        }

        dist_km: Optional[float] = None
        if "userLat" in q and "userLng" in q:
            dist_km = haversine_km(q["userLat"], q["userLng"], p.mapy, p.mapx)
        if dist_km is not None:
            data["distanceText"] = f"{dist_km}km"

        return Response(prune_empty(data))
