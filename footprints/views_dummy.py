from django.contrib.auth import get_user_model
from django.utils.timezone import now
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from places.models import Place
from .models import Footprint
from pets.models import PetProfile, PetBreed
from .data import HARDCODED_FOOTPRINTS

User = get_user_model()


def _footprint_has_field(field_name: str) -> bool:
    return any(getattr(f, "name", None) == field_name for f in Footprint._meta.get_fields())


def _ensure_seed_users():

    def upsert_user(handle: str, dog_name: str, size_code: str, breed_code: str):
        user, _ = User.objects.get_or_create(handle=handle, defaults={"is_active": True})

        breed = None
        if breed_code:
            breed, _ = PetBreed.objects.get_or_create(
                code=breed_code,
                defaults={"name_ko": breed_code.replace("-", " ").upper()},
            )

        dog, created = PetProfile.objects.get_or_create(
            user=user,
            defaults={"name": dog_name, "breed": breed, "size_code": size_code},
        )
        if not created:
            changed = False
            if not dog.name:
                dog.name = dog_name
                changed = True
            if breed and not dog.breed:
                dog.breed = breed
                changed = True
            if not dog.size_code:
                dog.size_code = size_code
                changed = True
            if changed:
                dog.save()
        return user

    return [
        upsert_user("seed_bot_1", "콩이",   PetProfile.Size.SMALL,  "mix-small"),
        upsert_user("seed_bot_2", "마루",   PetProfile.Size.MEDIUM, "mix-medium"),
        upsert_user("seed_bot_3", "흰둥이", PetProfile.Size.LARGE,  "mix-large"),
    ]


class DummyFootprintSeedView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="서버용:발자국 더미 데이터 저장",
        operation_description="각 장소에 리뷰를 2개씩 저장합니다.",
        tags=["Footprints"],
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "totalPlaces": openapi.Schema(type=openapi.TYPE_INTEGER),
                    "totalReviews": openapi.Schema(type=openapi.TYPE_INTEGER),
                    "created": openapi.Schema(type=openapi.TYPE_INTEGER),
                    "updated": openapi.Schema(type=openapi.TYPE_INTEGER),
                    "skipped": openapi.Schema(type=openapi.TYPE_INTEGER),
                    "missingPlaces": openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Items(type=openapi.TYPE_INTEGER),
                    ),
                    "timestamp": openapi.Schema(type=openapi.TYPE_STRING),
                },
            )
        },
        security=[],
    )
    def post(self, request):
        seed_users = _ensure_seed_users()
        has_rating = _footprint_has_field("rating")

        created = updated = skipped = 0
        total_reviews = 0
        missing_places = []

        for content_id, reviews in HARDCODED_FOOTPRINTS.items():
            try:
                place = Place.objects.get(content_id=content_id)
            except Place.DoesNotExist:
                missing_places.append(content_id)
                continue

            for idx, payload in enumerate(reviews or []):
                total_reviews += 1

                user = seed_users[idx % len(seed_users)]

                entry_status = payload.get("entryStatus")
                entry_detail = (payload.get("entryStatusDetail") or "").strip()
                if entry_status != "detail":
                    entry_detail = ""

                conditions = sorted(set(payload.get("conditions") or []))
                invalid = [c for c in conditions if c not in ["leash", "carrier", "leash_free", "diaper"]]
                if invalid:
                    skipped += 1
                    continue

                defaults = {
                    "entry_status": entry_status,
                    "entry_detail": entry_detail,
                    "conditions": conditions,
                    "welcome": int(payload.get("welcome", 3)),
                    "body": payload.get("body", ""),
                }
                if has_rating:
                    defaults["rating"] = int(payload.get("rating", 4))

                fp, was_created = Footprint.objects.update_or_create(
                    user=user,
                    place=place,
                    defaults=defaults,
                )
                if was_created:
                    created += 1
                else:
                    updated += 1

        return Response(
            {
                "totalPlaces": len(HARDCODED_FOOTPRINTS),
                "totalReviews": total_reviews,
                "created": created,
                "updated": updated,
                "skipped": skipped,
                "missingPlaces": missing_places,
                "timestamp": now().isoformat(),
            }
        )
