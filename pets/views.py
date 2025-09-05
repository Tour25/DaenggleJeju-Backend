from rest_framework import status
from django.db import transaction
from django.utils.text import slugify
from django.db.models import Q
from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import PetBreed
from .serializers import (
    PetBreedReadSerializer,
    PetBreedInitItemSerializer,
    PetBreedInitRequestSerializer,
)
from .breeds import PRESET_BREEDS

class PetBreedInitView(APIView):

    @swagger_auto_schema(
        operation_summary="견종 데이터 저장",
        request_body=None,
        tags=["Pets/Breeds"],
        responses={
            201: openapi.Response(
                description="시드 결과",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "created": openapi.Schema(type=openapi.TYPE_INTEGER),
                        "updated": openapi.Schema(type=openapi.TYPE_INTEGER),
                        "total":   openapi.Schema(type=openapi.TYPE_INTEGER),
                    },
                ),
            ),
        },
    )
    def post(self, request):
        items = [{"code": code, "nameKo": name} for code, name in PRESET_BREEDS]
        created = updated = 0
        with transaction.atomic():
            for row in items:
                obj, existed = PetBreed.objects.update_or_create(
                    code=row["code"],
                    defaults={"name_ko": row["nameKo"], "is_active": True},
                )
                if existed:
                    updated += 1
                else:
                    created += 1
        return Response(
            {"created": created, "updated": updated, "total": created + updated},
            status=status.HTTP_201_CREATED,
        )


class PetBreedSearchView(generics.ListAPIView):
    serializer_class = PetBreedReadSerializer
    pagination_class = None

    @swagger_auto_schema(
        operation_summary="견종 검색",
        tags=["Pets/Breeds"],
        manual_parameters=[
            openapi.Parameter(
                "q", openapi.IN_QUERY,
                description="검색어(한글명/코드 부분일치)",
                type=openapi.TYPE_STRING,
            ),
        ],
        responses={200: PetBreedReadSerializer(many=True)},
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        q = (self.request.query_params.get("q") or "").strip()
        qs = PetBreed.objects.filter(is_active=True)
        if q:
            slug_q = slugify(q, allow_unicode=True)
            qs = qs.filter(
                Q(name_ko__icontains=q) |
                Q(code__icontains=slug_q)
            )
        return qs.order_by("name_ko")
