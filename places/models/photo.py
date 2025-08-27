from django.db import models
from .base import TimeStampedModel
from .place import Place

class Photo(TimeStampedModel):
    place = models.ForeignKey(Place, on_delete=models.CASCADE, related_name="photos")
    image_url=models.URLField()
    description=models.CharField(max_length=225, blank=True, default="") #사진 설명
    is_cover=models.BooleanField(default=False) #대표 여부

    class Meta:
        unique_together=("place", "image_url")
        indexes=[models.Index(fields=["place"])]


    def __str__(self):
        return self.image_url
