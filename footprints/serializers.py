from rest_framework import serializers


class FootprintCreateSerializer(serializers.Serializer):
    contentId = serializers.IntegerField(help_text="장소 contentId")
    entryStatus = serializers.ChoiceField(choices=["allow", "deny", "detail"])
    entryStatusDetail = serializers.CharField(
        required=False, allow_blank=True, min_length=5, max_length=20,
        help_text="entryStatus=detail일 때 5~20자"
    )
    conditions = serializers.ListField(
        child=serializers.ChoiceField(choices=["leash", "carrier", "leash_free", "diaper"]),
        required=False, default=list, help_text="중복은 서버에서 제거됨"
    )
    welcome = serializers.ChoiceField(choices=[5, 4, 3, 2, 1])
    body = serializers.CharField(min_length=5, max_length=500)

    def validate(self, attrs):

        if attrs["entryStatus"] == "detail":
            detail = (attrs.get("entryStatusDetail") or "").strip()
            if not (5 <= len(detail) <= 20):
                raise serializers.ValidationError("entryStatusDetail은 5~20자여야 합니다.")
        else:

            attrs["entryStatusDetail"] = ""

        attrs["conditions"] = sorted(set(attrs.get("conditions", [])))
        return attrs


class MyFootprintListQuery(serializers.Serializer):
    contentTypeId = serializers.IntegerField(required=False)
    limit  = serializers.IntegerField(required=False, min_value=1, default=20)
    offset = serializers.IntegerField(required=False, min_value=0, default=0)
