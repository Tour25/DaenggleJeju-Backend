from django.db import models

class TimeStamped(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        abstract = True

class AreaCode(TimeStamped):
    area_code = models.CharField(max_length=8)
    sigungu_code = models.CharField(max_length=8, blank=True, null=True)
    name = models.CharField(max_length=100)

    class Meta:
        unique_together = ("area_code", "sigungu_code")
        indexes = [models.Index(fields=["area_code", "sigungu_code"])]

    def __str__(self):
        return f"{self.area_code}-{self.sigungu_code or ''} {self.name}"

class CategoryCode(TimeStamped):
    content_type_id = models.IntegerField()  # 12,14,15,28,32,38,39
    cat1 = models.CharField(max_length=10, blank=True, null=True)
    cat2 = models.CharField(max_length=10, blank=True, null=True)
    cat3 = models.CharField(max_length=10, blank=True, null=True)
    name = models.CharField(max_length=200)

    class Meta:
        indexes = [models.Index(fields=["content_type_id", "cat1", "cat2", "cat3"])]

class Place(TimeStamped):
    content_id = models.BigIntegerField(unique=True)
    content_type_id = models.IntegerField()
    title = models.CharField(max_length=300)

    addr1 = models.CharField(max_length=300, blank=True, null=True)
    mapx = models.FloatField(blank=True, null=True)
    mapy = models.FloatField(blank=True, null=True)
    modified_time = models.CharField(max_length=14, blank=True, null=True)  # YYYYMMDDhhmmss
    has_image = models.BooleanField(default=False)

    overview = models.TextField(blank=True, null=True)
    tel = models.CharField(max_length=100, blank=True, null=True)
    homepage = models.URLField(blank=True, null=True)

    meta_common = models.JSONField(default=dict)  # detailCommon 원문
    meta_intro = models.JSONField(default=dict)   # detailIntro 원문
    meta_info = models.JSONField(default=dict)    # detailInfo 원문

    def __str__(self):
        return f"[{self.content_type_id}] {self.title} ({self.content_id})"

class PlaceImage(TimeStamped):
    place = models.ForeignKey(Place, on_delete=models.CASCADE, related_name="images")
    origin = models.URLField()
    thumb = models.URLField(blank=True, null=True)

    class Meta:
        unique_together = ("place", "origin")

class PetPolicy(TimeStamped):
    place = models.OneToOneField(Place, on_delete=models.CASCADE, related_name="pet_policy")
    acmpy_type_cd = models.CharField(max_length=100, blank=True, null=True)
    etc_info = models.TextField(blank=True, null=True)
