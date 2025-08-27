from django.db import models
from .base import TimeStampedModel
from .place import Place

class PlaceDetailInfo(TimeStampedModel):
    place = models.ForeignKey(Place, on_delete=models.CASCADE, related_name="detail_infos")
    serialnum = models.CharField(max_length=10, blank=True, default="") #관광공사 일련번호
    infoname = models.CharField(max_length=100) #항목 이름
    infotext = models.TextField(blank=True, default="") #항목 값/설명
    infotype = models.CharField(max_length=10, blank=True, default="") #구분값

    class Meta:
        unique_together = ("place", "serialnum", "infoname")

    def __str__(self):
        return f"{self.place_id}:{self.infoname}"
