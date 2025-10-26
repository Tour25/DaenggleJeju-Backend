from rest_framework import serializers


class FootprintCreateSerializer(serializers.Serializer):
    contentId = serializers.IntegerField(help_text="장소 contentId")

    entryStatus = serializers.ChoiceField(
        choices=["allow", "deny", "detail"],
        label="출입 허용 범위",
        help_text="allow=출입 가능, deny=출입 불가, detail=상세 입력",
    )

    entryStatusDetail = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        help_text="entryStatus=detail(상세 입력)일 때만 5~20자"
    )

    conditions = serializers.ListField(
        child=serializers.ChoiceField(choices=["leash", "carrier", "leash_free", "diaper"]),
        required=False,
        default=list,
        help_text="leash(목줄), carrier(이동가방), leash_free(목줄 미착용), diaper(기저귀/매너벨트)",
    )

    welcome = serializers.ChoiceField(
        choices=[5, 4, 3, 2, 1],
        help_text="5(매우 친절) · 4(편안했어요) · 3(보통이에요) · 2(조금 어려웠어요) · 1(아쉬워요)",
    )


    rating = serializers.IntegerField(
        min_value=1,
        max_value=5,
        required=True,
        help_text="장소 별점(1~5)"
    )

    body = serializers.CharField(
        help_text="발자국 후기 - 최소 5글자 최대 500글자",
        min_length=5,
        max_length=500
    )

    def validate(self, attrs):

        if attrs["entryStatus"] == "detail":
            detail = (attrs.get("entryStatusDetail") or "").strip()
            if not (5 <= len(detail) <= 20):
                raise serializers.ValidationError("entryStatusDetail은 5~20자여야 합니다.")
            attrs["entryStatusDetail"] = detail
        else:

            attrs["entryStatusDetail"] = ""

        attrs["conditions"] = sorted(set(attrs.get("conditions", [])))

        return attrs


class MyFootprintListQuery(serializers.Serializer):
    contentTypeId = serializers.IntegerField(
        required=False,
        help_text="32=숙박, 39=음식점, 12=관광지, 28=레포츠, 38=쇼핑"
    )
    limit  = serializers.IntegerField(required=False, min_value=1, default=20)
    offset = serializers.IntegerField(required=False, min_value=0, default=0)


class PlaceFootprintListQuery(serializers.Serializer):
    limit  = serializers.IntegerField(required=False, min_value=1, default=20)
    offset = serializers.IntegerField(required=False, min_value=0, default=0)
