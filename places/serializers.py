from rest_framework import serializers

class PlaceMapAllQuery(serializers.Serializer):

    bbox = serializers.CharField(help_text="지도의 가시영역 BBOX: minLng,minLat,maxLng,maxLat (예: 126.2,33.2,126.7,33.6)")

    contentTypeId = serializers.IntegerField(
        required=False,
        help_text="예: 32=숙박, 39=음식점, 12=관광지, 28=레포츠, 38=쇼핑"
    )

    limit = serializers.IntegerField(required=False, min_value=1, max_value=100, default=100)

    sizes = serializers.ListField(
        child=serializers.ChoiceField(choices=["small", "med", "large", "xlarge", "all"]),
        required=False, default=[],
        help_text="반려견 크기: small(10↓), med(10~24), large(25~44), xlarge(45↑), all(소/중/대/초대형 모두)"
    )
    areas = serializers.ListField(
        child=serializers.ChoiceField(choices=["indoor", "outdoor", "allarea"]),
        required=False, default=[],
        help_text="출입 가능 장소: indoor/ outdoor/ allarea(모든 구역)"
    )
    conditions = serializers.ListField(
        child=serializers.ChoiceField(choices=["leash", "carrier", "leash_free", "diaper"]),
        required=False, default=[],
        help_text="출입 조건: leash(목줄), carrier(이동가방), leash_free(자유), diaper(기저귀)"
    )
    amenities = serializers.ListField(
        child=serializers.ChoiceField(choices=[
            "parking", "bbq", "wifi", "takeout", "yard", "pets_zone", "barking_ok", "jacuzzi"
        ]),
        required=False, default=[],
        help_text="편의: parking(주차), bbq, wifi, takeout, yard(마당), pets_zone(애견전용), barking_ok, jacuzzi"
    )

class PlaceDetailQuery(serializers.Serializer):
    userLat = serializers.FloatField(required=False)
    userLng = serializers.FloatField(required=False)