from rest_framework import serializers
from .models import MemberPreference

STYLE_CHOICES = ("RELAX", "OUTDOOR", "RESORT", "CAFE", "ACTIVITY")

REGION_PLACE_CHOICES = ("PLACE_jeju_si","PLACE_aeweol","PLACE_jocheon","PLACE_seogwipo_si","PLACE_andeok", "PLACE_seongsan")

class MemberPreferenceWriteSerializer(serializers.Serializer):
    regionContextIds = serializers.ListField(
        child=serializers.ChoiceField(choices=REGION_PLACE_CHOICES),
        allow_empty=True,
        help_text=" 선호 지역:"
                  " PLACE_jeju_si: 제주시 | PLACE_aeweol: 애월/한림/한경 | PLACE_jocheon:조천/구좌/우도"
                  " PLACE_seogwipo_si: 서귀포시 | PLACE_andeok: 안덕/대정 | PlACE_seongsan: 성산/표선/남원",)

    styleCodes = serializers.ListField(
        child=serializers.ChoiceField(choices=STYLE_CHOICES),
        allow_empty=True,
        help_text="여행 스타일:"
                  "RELAX:1번, OUTDOOR:2번, RESORT: 3번, CAFE: 4번, ACTIVITY:5번",
    )
    class Meta:
        swagger_schema_fields = {
            "example": {
                "regionContextIds": ["PLACE_aeweol", "PLACE_jocheon"],
                "styleCodes": ["RELAX", "CAFE"]
            }
        }

class MemberPreferenceReadSerializer(serializers.ModelSerializer):
    regionContextIds = serializers.ListField(source="region_context_ids")
    styleCodes = serializers.ListField(source="style_codes")

    class Meta:
        model = MemberPreference
        fields = ("regionContextIds", "styleCodes")
