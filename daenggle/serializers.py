from rest_framework import serializers

class ShortsQuery(serializers.Serializer):
    type = serializers.ChoiceField(
        choices=[ "trending", "accommodation", "place"],
        help_text = "피드 유형\n"
                    "trending:조회수 | accommodation: 숙소 | place: 지역"
    )

    sort= serializers.ChoiceField(choices=["rank", "recent", "views"], default="rank")
    limit= serializers.IntegerField(min_value=1, max_value=50, default=20)
    offset= serializers.IntegerField(min_value=0, default=0)



REGION_PLACE_CHOICES = (
    "PLACE_jeju_si","PLACE_aeweol","PLACE_jocheon",
    "PLACE_seogwipo_si","PLACE_andeok","PLACE_seongsan",
)

class RegionShortsQuery(serializers.Serializer):
    contextId = serializers.ChoiceField(choices=REGION_PLACE_CHOICES, help_text="조회할 지역 context_id (필수)")
    sort = serializers.ChoiceField(choices=["rank","recent","views"], default="rank", help_text="정렬: rank(추천)/recent(최신)/views(조회수)")
    limit = serializers.IntegerField(min_value=1, max_value=50, default=20, help_text="가져올 개수")
    offset = serializers.IntegerField(min_value=0, default=0, help_text="페이지 오프셋(views 또는 간단 페이지네이션용)")
    excludeIds = serializers.ListField(
        child=serializers.CharField(), required=False, default=[],
        help_text="이미 본 YouTube video_id 목록(중복 방지)"
    )


class ConceptQuery(serializers.Serializer):
    conceptKeys = serializers.ListField(
        child=serializers.CharField(),
        required=False, default=[],
        help_text="조회할 컨셉 key 배열. 비우면 모든 컨셉을 조회 (daenggle/presets.py의 CURATION_TILES 참조)"
    )
    limitPerConcept = serializers.IntegerField(
        min_value=1, max_value=20, default=8,
        help_text="컨셉당 반환할 영상 수 (기본 8)"
    )

    class Meta:
        swagger_schema_fields = {
            "example": {
                "conceptKeys": ["water_activity", "aeweol_coastal_road"],
                "limitPerConcept": 8
            }
        }