from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema

from .models import MemberPreference
from .serializers import MemberPreferenceWriteSerializer, MemberPreferenceReadSerializer


class MemberPreferenceUpsertView(APIView):
    @swagger_auto_schema(
        operation_summary="큐레이션 선호하는 여행 스타일 저장",
        tags=["Members"],
        request_body=MemberPreferenceWriteSerializer,
        responses={200: MemberPreferenceReadSerializer},
    )
    def post(self, request):
        ser = MemberPreferenceWriteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        pref, _ = MemberPreference.objects.get_or_create(user=request.user)
        pref.region_context_ids = ser.validated_data["regionContextIds"]
        pref.style_codes = ser.validated_data["styleCodes"]
        pref.save()

        return Response(MemberPreferenceReadSerializer(pref).data, status=status.HTTP_200_OK)