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
