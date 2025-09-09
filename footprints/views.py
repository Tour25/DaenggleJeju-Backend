from django.shortcuts import get_object_or_404
from django.utils.timezone import localtime
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from typing import Optional

from places.models import Place, PlaceImage
from places.constants import CONTENT_TYPE_LABELS
from .models import Footprint
from .serializers import FootprintCreateSerializer, MyFootprintListQuery
from places.utils import address_brief, thumb_or_text, haversine_km, place_type_label, prune_empty

COND_LABELS = {
    "leash": "목줄 착용",
    "carrier": "이동 가방",
    "leash_free": "자유",
    "diaper": "기저귀",
}
WELCOME_LABELS = {
    5: "매우 친절",
    4: "편안했어요",
    3: "보통이에요",
    2: "조금 어려웠어요",
    1: "아쉬워요",
}
ENTRY_LABELS = {
    "allow": "출입 가능",
    "deny": "출입 불가",
    "detail": None,
}


def _entry_chip(fp: Footprint) -> Optional[str]:
    if fp.entry_status == "detail":
        return (fp.entry_status_detail or "").strip() or None
    return ENTRY_LABELS.get(fp.entry_status)


def _conditions_chip(fp: Footprint) -> Optional[str]:
    if not fp.conditions:
        return None
    labels = [COND_LABELS.get(c, c) for c in fp.conditions if c]
    return " · ".join(labels) if labels else None


def _welcome_chip(fp: Footprint) -> Optional[str]:
    return WELCOME_LABELS.get(fp.welcome)

class FootprintCreateView(APIView):

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="발자국 남기기",
        tags=["Footprints"],
        request_body=FootprintCreateSerializer,
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "footprintId": openapi.Schema(type=openapi.TYPE_INTEGER),
                    "contentId": openapi.Schema(type=openapi.TYPE_INTEGER),
                    "created": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                    "message": openapi.Schema(type=openapi.TYPE_STRING),
                },
            ),
            201: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "footprintId": openapi.Schema(type=openapi.TYPE_INTEGER),
                    "contentId": openapi.Schema(type=openapi.TYPE_INTEGER),
                    "created": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                    "message": openapi.Schema(type=openapi.TYPE_STRING),
                },
            ),
        },
    )
    def post(self, request):
        s = FootprintCreateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data

        place = get_object_or_404(Place, content_id=d["contentId"])

        fp, created = Footprint.objects.update_or_create(
            user=request.user, place=place,
            defaults={
                "entry_status": d["entryStatus"],
                "entry_detail": d.get("entryStatusDetail", ""),
                "conditions":   d.get("conditions", []),
                "welcome":      int(d["welcome"]),
                "body":         d["body"],
            },
        )

        return Response(
            {
                "footprintId": fp.id,
                "contentId": place.content_id,
                "created": created,
                "message": "발자국을 남겼어요" if created else "발자국을 업데이트했어요",
            },
            status=201 if created else 200,
        )


class MyFootprintsListView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="내가 작성한 발자국 목록 조회",
        tags=["Footprints"],
        query_serializer=MyFootprintListQuery,
    )
    def get(self, request):
        s = MyFootprintListQuery(data=request.query_params)
        s.is_valid(raise_exception=True)
        q = s.validated_data

        qs = (
            Footprint.objects
            .filter(user=request.user)
            .select_related("place", "place__pet_policy")
            .prefetch_related("place__images")
            .order_by("-created_at")
        )
        if q.get("contentTypeId"):
            qs = qs.filter(place__content_type_id=q["contentTypeId"])

        start = q.get("offset", 0)
        end = start + q.get("limit", 20)
        rows = list(qs[start:end])

        user_lat = q.get("userLat")
        user_lng = q.get("userLng")

        items = []
        for fp in rows:
            p: Place = fp.place

            chips = []
            entry_chip = _entry_chip(fp)
            cond_chip  = _conditions_chip(fp)
            welc_chip  = _welcome_chip(fp)
            if entry_chip: chips.append(entry_chip)
            if cond_chip:  chips.append(cond_chip)
            if welc_chip:  chips.append(welc_chip)

            created = localtime(fp.created_at)
            created_text = created.strftime("%Y.%m.%d")

            dist_text = None
            if user_lat is not None and user_lng is not None and p.mapy is not None and p.mapx is not None:
                d = haversine_km(user_lat, user_lng, p.mapy, p.mapx)
                if d is not None:
                    dist_text = f"{d}km"

            item = {
                "footprintId": fp.id,
                "contentId": p.content_id,
                "contentType": {
                    "id": p.content_type_id,
                    "name": CONTENT_TYPE_LABELS.get(p.content_type_id, "기타"),
                },
                "title": p.title,
                "metaLine": f"{address_brief(p.addr1)} · {place_type_label(p) or ''}".rstrip(" ·"),
                "createdAt": created.isoformat(),
                "createdAtText": created_text,
                "distanceText": dist_text,
                "thumbnail": thumb_or_text(p),
                "chips": chips,
                "welcome": fp.welcome,
                "body": fp.body,
            }
            items.append(prune_empty(item))

        return Response({"total": Footprint.objects.filter(user=request.user).count(), "items": items})