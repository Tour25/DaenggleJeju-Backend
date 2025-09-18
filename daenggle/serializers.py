from rest_framework import serializers
from .presets import CURATION_TILES

def _concept_key_choices():
    return [(c["key"], c["title"]) for c in CURATION_TILES]

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

class TrendingShortsQuery(serializers.Serializer):
    sort = serializers.ChoiceField(choices=["rank", "recent", "views"], default="views",
                                   help_text="정렬: rank(추천)/recent(최신)/views(조회수)")
    days = serializers.IntegerField(min_value=1, max_value=90, required=False, default=90,
                                    help_text="최근 N일 이내 (기본 90일)")
    limit = serializers.IntegerField(min_value=1, max_value=50, default=20)
    offset = serializers.IntegerField(min_value=0, default=0)

class AccommodationShortsQuery(serializers.Serializer):
    sort = serializers.ChoiceField(choices=["rank", "recent", "views"], default="rank")
    limit = serializers.IntegerField(min_value=1, max_value=50, default=20)
    offset = serializers.IntegerField(min_value=0, default=0)

class ConceptQuery(serializers.Serializer):
    conceptKeys = serializers.ListField(
        child=serializers.ChoiceField(choices=_concept_key_choices()),
        required=False,
        default=[],
        help_text="조회할 컨셉 key 배열. 비우면 모든 컨셉 조회"
    )
    limitPerConcept = serializers.IntegerField(
        min_value=1, max_value=20, default=8,
        help_text="컨셉당 반환할 영상 수 (기본 8)"
    )

    class Meta:
        swagger_schema_fields = {
            "example": {
                "conceptKeys": [CURATION_TILES[0]["key"], CURATION_TILES[1]["key"]],
                "limitPerConcept": 8
            }
        }


class ShortsSearchQuery(serializers.Serializer):
    q = serializers.CharField(min_length=2, help_text="검색어 (공백/쉼표 구분, 최소 2자)")
    sort = serializers.ChoiceField(choices=["rank", "recent", "views"], default="rank")
    limit = serializers.IntegerField(min_value=1, max_value=50, default=20)
    offset = serializers.IntegerField(min_value=0, default=0)


class PlaceRecommendQuery(serializers.Serializer):
    sort  = serializers.ChoiceField(choices=["rank", "recent", "views"], default="rank")
    limit = serializers.IntegerField(min_value=1, max_value=50, default=20)
    offset= serializers.IntegerField(min_value=0, default=0)


class PlaceDaenggleItemSerializer(serializers.Serializer):
    video_id = serializers.CharField()
    playbackUrl = serializers.CharField()

class PlaceDaenggleResponseSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    items = PlaceDaenggleItemSerializer(many=True)