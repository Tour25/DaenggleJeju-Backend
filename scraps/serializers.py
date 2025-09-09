from rest_framework import serializers

class ScrapSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=["place"], help_text="스크랩 대상, 현재는 place만")
    id = serializers.IntegerField(help_text="장소 contentId")

class ScrapListQuery(serializers.Serializer):
    type = serializers.ChoiceField(choices=["place"], help_text="스크랩 대상, 현재는 place만")
    limit  = serializers.IntegerField(required=False, min_value=1, default=50)
    offset = serializers.IntegerField(required=False, min_value=0, default=0)
    userLat = serializers.FloatField(required=False, help_text="사용자의 현재 위치 위도")
    userLng = serializers.FloatField(required=False, help_text="사용자의 현재 위치 경도")
