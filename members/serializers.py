# member/serializers.py

from rest_framework import serializers
from .models import MemberPreference

STYLE_CHOICES = ("RELAX", "OUTDOOR", "RESORT", "CAFE", "ACTIVITY")

class MemberPreferenceWriteSerializer(serializers.Serializer):
    regionContextIds = serializers.ListField(
        child=serializers.RegexField(r"^(PLACE|ACC)_[a-z0-9_\-]+$"),
        allow_empty=True
    )
    styleCodes = serializers.ListField(
        child=serializers.ChoiceField(choices=STYLE_CHOICES),
        allow_empty=True
    )
    class Meta:
        swagger_schema_fields = {
            "example": {
                "regionContextIds": ["PLACE_aeweol", "PLACE_seongsan"],
                "styleCodes": ["RELAX", "CAFE"]
            }
        }

class MemberPreferenceReadSerializer(serializers.ModelSerializer):
    regionContextIds = serializers.ListField(source="region_context_ids")
    styleCodes = serializers.ListField(source="style_codes")

    class Meta:
        model = MemberPreference
        fields = ("regionContextIds", "styleCodes")
