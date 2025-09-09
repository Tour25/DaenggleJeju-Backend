from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_yasg import openapi

from places.models import Place
from places.constants import CONTENT_TYPE_LABELS, SIZE_KEYWORDS, AREA_KEYWORDS, AMENITY_KEYWORDS
from places.utils import (
    address_brief, collect_text, find_labels, thumb_or_text,
    conditions_text, haversine_km, prune_empty, place_type_label,
)
from .models import Scrap
from .serializers import ScrapSerializer, ScrapListQuery


def _ct_for(model):
    return ContentType.objects.get_for_model(model)


def _place_to_card(p, user_lat=None, user_lng=None):
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

    dist_text = None
    if user_lat is not None and user_lng is not None:
        d = haversine_km(user_lat, user_lng, p.mapy, p.mapx)
        if d is not None:
            dist_text = f"{d}km"

    return prune_empty({
        "contentId": p.content_id,
        "contentType": {"id": p.content_type_id, "name": CONTENT_TYPE_LABELS.get(p.content_type_id, "기타")},
        "title": p.title,
        "metaLine": f"{address_brief(p.addr1)} · {place_type_label(p) or ''}".rstrip(" ·"),
        "distanceText": dist_text,
        "thumbnail": thumb_or_text(p),
        "chips": chips,
        "isScrapped": True,
    })


def _content_type_for(model):
    return ContentType.objects.get_for_model(model)

class ScrapView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="스크랩 추가/삭제",
        operation_description="스크랩을 추가하거나 삭제합니다. type에 따라 대상을 분리합니다. 현재는 place만",
        tags=["Scraps"],
        request_body=ScrapSerializer,
        responses={
            200: openapi.Response(
                description="OK",
                examples={
                    "application/json": {
                        "type": "place",
                        "id": 3112043,
                        "scraped": True,
                        "message": "스크랩되었습니다"
                    }
                },
            ),
            400: "Bad Request",
            404: "Not Found",
        },
    )
    def post(self, request):
        s = ScrapSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        t = s.validated_data["type"]
        obj_id = s.validated_data["id"]

        if t != "place":
            return Response({"detail": "unsupported type"}, status=400)

        try:
            place = Place.objects.get(content_id=obj_id)
        except Place.DoesNotExist:
            return Response({"detail": "Not found."}, status=404)

        ct = _content_type_for(Place)

        with transaction.atomic():
            scrap, created = Scrap.objects.get_or_create(
                user=request.user, content_type=ct, object_id=place.pk
            )
            if not created:

                scrap.delete()
                return Response({
                    "type": "place",
                    "id": obj_id,
                    "scraped": False,
                    "message": "스크랩이 취소되었습니다"
                })

            return Response({
                "type": "place",
                "id": obj_id,
                "scraped": True,
                "message": "스크랩되었습니다"
            })


class ScrapListView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(operation_summary="내가 스크랩 한 장소 목록 조회",
                         operation_description="사용자 본인이 스크랩 한 장소를 전체 조회합니다. type: place",
                         tags=["Scraps"],
                         query_serializer=ScrapListQuery)
    def get(self, request):
        s = ScrapListQuery(data=request.query_params)
        s.is_valid(raise_exception=True)
        q = s.validated_data

        if q["type"] != "place":
            return Response({"detail": "unsupported type"}, status=400)

        ct = _ct_for(Place)
        scraps_qs = Scrap.objects.filter(user=request.user, content_type=ct).order_by("-created_at")

        total = scraps_qs.count()
        start = q.get("offset", 0)
        end = start + q.get("limit", 50)
        scraps = list(scraps_qs[start:end])

        pks = [sc.object_id for sc in scraps]
        places = (Place.objects.filter(pk__in=pks)
                  .select_related("pet_policy")
                  .prefetch_related("images"))

        order = {pk: i for i, pk in enumerate(pks)}
        places = sorted(places, key=lambda p: order.get(p.pk, 10**9))

        user_lat = q.get("userLat")
        user_lng = q.get("userLng")
        items = [_place_to_card(p, user_lat, user_lng) for p in places]

        return Response({"total": total, "items": items})
