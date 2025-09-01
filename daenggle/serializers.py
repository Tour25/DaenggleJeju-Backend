from rest_framework import serializers

class ShortsQuery(serializers.Serializer):
    type = serializers.ChoiceField(choices=[
        "trending", "accommodation", "place", "keyword"
    ])
    contextId= serializers.CharField(required=False, allow_blank=True, default="")
    keyword= serializers.CharField(required=False, allow_blank=True, default="")
    sort= serializers.ChoiceField(choices=["rank", "recent", "views"], default="rank")
    limit= serializers.IntegerField(min_value=1, max_value=50, default=20)
    offset= serializers.IntegerField(min_value=0, default=0)  # ← 심플한 페이지네이션

    # 품질 필터(있으면 적용)
    days= serializers.IntegerField(required=False, min_value=1, max_value=365, default=None)
    maxDuration= serializers.IntegerField(required=False, min_value=1, max_value=600, default=None)
