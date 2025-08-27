from django.db import models
from .base import TimeStampedModel
from .place import Place

class PetPolicy(TimeStampedModel):
    place = models.OneToOneField(Place, on_delete=models.CASCADE, related_name="pet_policy")

    companion_type=models.CharField(max_length=100, blank=True, default="") #반려견 동반 가능 유형
    allowed_pets=models.CharField(max_length=225, blank=True, default="") #동반 가능 동물
    required_items=models.CharField(max_length=225, blank=True, default="") #필수 준비물
    extra_info=models.TextField(blank=True, default="") #기타 안내사항

    def __str__(self):
        return f"PetPolicy <{self.place_id}>"