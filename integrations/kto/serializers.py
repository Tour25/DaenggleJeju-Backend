from rest_framework import serializers

class AreaBasedListQuery(serializers.Serializer):
    areaCode = serializers.CharField()
    sigunguCode = serializers.CharField(required=False, allow_blank=True)
    pageNo = serializers.IntegerField(required=False, default=1)
    numOfRows = serializers.IntegerField(required=False, default=100)
    arrange = serializers.ChoiceField(required=False, default="C",
        choices=["A","B","C","D","E","O","Q","R","S"])
    listYN = serializers.ChoiceField(required=False, default="Y", choices=["Y","N"])

class LocationBasedListQuery(serializers.Serializer):
    mapX = serializers.FloatField()
    mapY = serializers.FloatField()
    radius = serializers.IntegerField(default=20000)
    pageNo = serializers.IntegerField(required=False, default=1)
    numOfRows = serializers.IntegerField(required=False, default=100)
    arrange = serializers.ChoiceField(required=False, default="E",
        choices=["E","S","A","B","C","D","O","Q","R","S"])
    listYN = serializers.ChoiceField(required=False, default="Y", choices=["Y","N"])

class SearchKeywordQuery(serializers.Serializer):
    keyword = serializers.CharField()
    areaCode = serializers.CharField(required=False, allow_blank=True)
    sigunguCode = serializers.CharField(required=False, allow_blank=True)
    pageNo = serializers.IntegerField(required=False, default=1)
    numOfRows = serializers.IntegerField(required=False, default=100)
    arrange = serializers.ChoiceField(required=False, default="C",
        choices=["A","B","C","D","O","Q","R","S"])
    listYN = serializers.ChoiceField(required=False, default="Y", choices=["Y","N"])

class PetTourSyncQuery(serializers.Serializer):
    modifiedtime = serializers.RegexField(r"^\d{8}$")  # YYYYMMDD
    showflag = serializers.IntegerField(required=False, default=1)
    pageNo = serializers.IntegerField(required=False, default=1)
    numOfRows = serializers.IntegerField(required=False, default=100)
    dry_run = serializers.BooleanField(required=False, default=True)

class BootstrapAreaBody(serializers.Serializer):
    areaCode = serializers.CharField()                 # 예: "39" (제주)
    sigunguCode = serializers.CharField(required=False, allow_blank=True, default="")
    numOfRows = serializers.IntegerField(required=False, default=100)
    max_pages = serializers.IntegerField(required=False, default=999)

class EnrichIdsBody(serializers.Serializer):
    ids = serializers.ListField(child=serializers.IntegerField(), min_length=1, max_length=1000)
