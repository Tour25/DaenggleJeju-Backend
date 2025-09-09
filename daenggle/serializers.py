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