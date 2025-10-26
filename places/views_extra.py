# -*- coding: utf-8 -*-
import hashlib
from django.db import transaction
from django.utils.timezone import now
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from places.models import Place, PlaceImage, PetPolicy
from .place_extra_data import EXTRA_PLACES

CATEGORY_TO_CTID = {
    "관광지": 12,
    "문화시설": 14,
    "레포츠": 28,
    "숙박": 32,
    "음식점": 39,
}

def _ctid_from_kor(category_name: str) -> int:
    if not category_name:
        raise ValueError("category 누락")
    for k, v in CATEGORY_TO_CTID.items():
        if k in str(category_name):
            return v
    raise ValueError(f"알 수 없는 카테고리: {category_name!r}")

def _synthetic_content_id(title: str, addr1: str = "") -> int:

    base = 900_000_000
    key = f"{title}@@{addr1}".encode("utf-8")
    digest_int = int(hashlib.md5(key).hexdigest(), 16)
    return base + (digest_int % 99_999_999)

def _clean(s):
    if s is None:
        return None
    s = str(s).strip()
    return s or None

class PlaceExtraSeedView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="서버용:장소 더미데이터 저장-필수 실행",
        operation_description="장소 데이터를 저장합니다.",
        tags=["Places"],
        responses={200: openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "total": openapi.Schema(type=openapi.TYPE_INTEGER),
                "created": openapi.Schema(type=openapi.TYPE_INTEGER),
                "updated": openapi.Schema(type=openapi.TYPE_INTEGER),
                "errors": openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING)),
                "ids": openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_INTEGER)),
                "timestamp": openapi.Schema(type=openapi.TYPE_STRING),
            }
        )},
        security=[],
    )
    def post(self, request):
        created = updated = 0
        errors = []
        ids = []

        with transaction.atomic():
            for i, row in enumerate(EXTRA_PLACES, start=1):
                try:
                    title = _clean(row.get("title"))
                    if not title:
                        raise ValueError(f"{i}행: title 누락")

                    category = _clean(row.get("category"))
                    ctid = _ctid_from_kor(category)

                    addr1 = _clean(row.get("addr1"))
                    content_id = row.get("content_id")
                    if content_id is None:
                        content_id = _synthetic_content_id(title, addr1 or "")

                    defaults = {
                        "content_type_id": ctid,
                        "title": title,
                        "addr1": addr1,
                        "mapx": row.get("mapx"),
                        "mapy": row.get("mapy"),
                        "modified_time": None,
                        "has_image": bool(_clean(row.get("thumbnail"))),
                        "overview": None,
                        "tel": _clean(row.get("tel")),
                        "homepage": _clean(row.get("homepage")),
                        "has_parking": row.get("has_parking"),
                        "parking_note": _clean(row.get("parking_note")),
                        "usetime": _clean(row.get("usetime")),
                        "restdate": _clean(row.get("restdate")),
                        "opendate": _clean(row.get("opendate")),
                        "useseason": _clean(row.get("useseason")),
                        "accomcount": _clean(row.get("accomcount")),
                        "expagerange": _clean(row.get("expagerange")),
                        "expguide": _clean(row.get("expguide")),
                        "chkcreditcard": _clean(row.get("chkcreditcard")),
                        "accepts_card": row.get("accepts_card"),
                        "meta_common": row.get("meta_common") or {},
                        "meta_intro": row.get("meta_intro") or {},
                        "meta_info": row.get("meta_info") or {},
                    }

                    place, was_created = Place.objects.update_or_create(
                        content_id=content_id, defaults=defaults
                    )
                    ids.append(place.content_id)
                    if was_created:
                        created += 1
                    else:
                        updated += 1

                    thumb = _clean(row.get("thumbnail"))
                    if thumb:
                        PlaceImage.objects.get_or_create(place=place, origin=thumb)

                    chips = _clean(row.get("chips"))
                    notes = _clean(row.get("notes"))
                    etc_lines = []
                    if chips:
                        etc_lines.append(f"[chips] {chips}")
                    if notes:
                        etc_lines.append(f"[notes] {notes}")
                    if etc_lines:
                        PetPolicy.objects.update_or_create(
                            place=place,
                            defaults={"acmpy_type_cd": None, "etc_info": "\n".join(etc_lines)},
                        )

                except Exception as e:
                    errors.append(f"row#{i} ({row.get('title')!r}): {e}")

        return Response({
            "total": len(EXTRA_PLACES),
            "created": created,
            "updated": updated,
            "errors": errors,
            "ids": ids,
            "timestamp": now().isoformat(),
        })
