from rest_framework import serializers
from daenggle.models import DaenggleTag

class YouTubeSyncRequest(serializers.Serializer):
    keywords = serializers.ListField(child=serializers.CharField(), allow_empty=False)
    days = serializers.IntegerField(min_value=1, max_value=180, default=60)
    pages = serializers.IntegerField(min_value=1, max_value=3, default=1)
    maxDuration = serializers.IntegerField(min_value=1, max_value=300, default=90)
    category = serializers.ChoiceField(
        choices=[c for c, _ in DaenggleTag.Category.choices],
        default=DaenggleTag.Category.TREND
    )
    contextId = serializers.CharField(required=False, allow_blank=True, default="")
    contextName = serializers.CharField(required=False, allow_blank=True, default="")


class BatchSyncBody(serializers.Serializer):
    include = serializers.ListField(
        child=serializers.ChoiceField(["trending", "place", "accommodation"]),
        required=False,
        default=["trending", "place", "accommodation"],
        help_text="돌릴 대상 선택 (기본: 전부)"
    )
    days = serializers.IntegerField(required=False, default=90)
    pages = serializers.IntegerField(required=False, default=1)
    maxDuration = serializers.IntegerField(required=False, allow_null=True, default=120)

