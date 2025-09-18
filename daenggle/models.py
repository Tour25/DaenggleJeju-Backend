from django.db import models
from places.models import Place

class DaenggleClip(models.Model):
    video_id = models.CharField(max_length=20, unique=True, db_index=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    channel_title = models.CharField(max_length=255, blank=True)
    published_at = models.DateTimeField(db_index=True)
    duration_seconds = models.IntegerField(null=True, blank=True)
    view_count = models.BigIntegerField(null=True, blank=True)
    like_count = models.BigIntegerField(null=True, blank=True)
    thumbnails = models.JSONField(default=dict, blank=True)
    tags = models.JSONField(default=list, blank=True)
    etag = models.CharField(max_length=128, blank=True)
    fetched_at = models.DateTimeField(auto_now=True)

    styles = models.JSONField(default=list, blank=True)
    style_meta = models.JSONField(default=dict, blank=True)

def __str__(self):
        return f"{self.title} ({self.video_id})"


class DaenggleTag(models.Model):
    class Category(models.TextChoices):
        KEYWORD = "KEYWORD", "KEYWORD"
        PLACE = "PLACE", "PLACE"
        ACCOMMODATION = "ACCOMMODATION", "ACCOMMODATION"
        TREND = "TREND", "TREND"

    category = models.CharField(max_length=32, choices=Category.choices)
    keyword = models.CharField(max_length=200, blank=True)

    context_id = models.CharField(max_length=64, blank=True)
    context_name = models.CharField(max_length=255, blank=True)

    clip = models.ForeignKey(
        DaenggleClip, on_delete=models.CASCADE, related_name="tagging"
    )

    class Meta:
        unique_together = (("category", "context_id", "clip"),)


class PlaceDaenggle(models.Model):
    place = models.ForeignKey(
        Place, on_delete=models.CASCADE, related_name="daenggle_videos"
    )
    video_id = models.CharField(max_length=20, db_index=True)

    class Meta:
        unique_together = ("place", "video_id")

    def __str__(self):
        return f"{self.place.title} - {self.video_id}"