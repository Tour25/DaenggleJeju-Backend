from rest_framework import serializers

class ScrapSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=["place"])
    id = serializers.IntegerField(help_text="place는 contentId")

class ScrapListQuery(serializers.Serializer):
    type = serializers.ChoiceField(choices=["place"])
    limit  = serializers.IntegerField(required=False, min_value=1, default=50)
    offset = serializers.IntegerField(required=False, min_value=0, default=0)
    userLat = serializers.FloatField(required=False)
    userLng = serializers.FloatField(required=False)
