from rest_framework import status
from django.db import transaction
from django.utils.text import slugify
from django.db.models import Q
from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated

from rest_framework.exceptions import ValidationError, NotFound
from common.exceptions import AppError

from .models import PetBreed, PetProfile
from .serializers import PetBreedReadSerializer, PetProfileWriteSerializer, PetProfileReadSerializer, PetProfilePatchSerializer
from .breeds import PRESET_BREEDS

class PetBreedInitView(APIView):

    @swagger_auto_schema(
        operation_summary="서버용: 견종 데이터 저장 - 필수 실행",
        operation_description="견종 정보를 저장합니다. 견종 검색 및 저장을 위해 실행해주세요. 서버용 api입니다.",
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
        operation_description="견종을 검색합니다.",
        tags=["Pets/Breeds"],
        manual_parameters=[
            openapi.Parameter(
                name="q",
                in_=openapi.IN_QUERY,
                description="검색어(한글명/코드 부분일치). 예: '골든', '말티', 'retriever'",
                type=openapi.TYPE_STRING,
                required=False,
            ),
        ],
        responses={200: PetBreedReadSerializer(many=True)},
    )
    def get(self, request, *args, **kwargs):
        request._resp_message = "견종 검색 결과"
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        qs = PetBreed.objects.filter(is_active=True)
        q = (self.request.query_params.get("q") or "").strip()

        if not q:
            return qs.order_by("name_ko")

        slug_q = slugify(q, allow_unicode=True)
        matched = qs.filter(
            Q(name_ko__icontains=q) |
            Q(code__icontains=slug_q)
        ).order_by("name_ko")

        if matched.exists():
            return matched

        other = qs.filter(code="other")
        return other if other.exists() else PetBreed.objects.none()


class PetProfileCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="반려견 프로필 저장",
        operation_description="반려견 프로필을 저장합니다.",
        tags=["Pets/Profiles"],
        request_body=PetProfileWriteSerializer,
        responses={201: PetProfileReadSerializer},
    )
    def post(self, request):
        ser = PetProfileWriteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        v = ser.validated_data

        breed = None
        if v.get("breedId") is not None:
            breed = PetBreed.objects.filter(id=v["breedId"], is_active=True).first()
            if not breed:
                raise AppError("유효하지 않은 breedId 입니다.", status_code=400, code="BREED_INVALID")

        pet = PetProfile.objects.create(
            user=request.user,
            name=v["name"],
            size_code=v["sizeCode"],
            breed=breed,
            birth_date=v.get("birthDate"),
        )
        request._resp_message = "반려견 프로필이 저장되었습니다."
        return Response(PetProfileReadSerializer(pet).data, status=status.HTTP_201_CREATED)

class PetProfileView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="반려견 프로필  조회",
        operation_description="내 반려견 프로필을 조회합니다.",
        tags=["Pets/Profiles"],
        responses={
            200: PetProfileReadSerializer,
            404: openapi.Response("Not Found"),
        },
    )
    def get(self, request, petId: int):
        try:
            pet = (PetProfile.objects
                   .select_related("breed")
                   .get(pk=petId, user=request.user))
        except PetProfile.DoesNotExist:
            raise AppError("반려견 프로필을 찾을 수 없습니다.", status_code=404, code="PET_PROFILE_NOT_FOUND")

        request._resp_message = "반려견 프로필 조회"
        return Response(PetProfileReadSerializer(pet).data)

class PetProfileUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="반려견 프로필 수정",
        operation_description="내 반려견 프로필을 부분 수정합니다.",
        tags=["Pets/Profiles"],
        request_body=PetProfilePatchSerializer,
        responses={200: PetProfileReadSerializer},
    )
    def patch(self, request, petId: int):
        pet = get_object_or_404(PetProfile, pk=petId, user=request.user)

        s = PetProfilePatchSerializer(data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        v = s.validated_data

        if "name" in v:
            pet.name = v["name"]
        if "sizeCode" in v:
            pet.size_code = v["sizeCode"]
        if "breedId" in v:
            breed = None
            if v["breedId"] is not None:
                breed = PetBreed.objects.filter(id=v["breedId"], is_active=True).first()
                if not breed:
                    raise AppError("유효하지 않은 breedId 입니다.", status_code=400, code="BREED_INVALID")
            pet.breed = breed
        if "birthDate" in v:
            pet.birth_date = v["birthDate"]

        pet.save()
        request._resp_message = "반려견 프로필이 수정되었습니다."
        return Response(PetProfileReadSerializer(pet).data, status=status.HTTP_200_OK)


