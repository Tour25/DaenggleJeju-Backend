from django.conf import settings
from django.db import models
from places.models import Place


class EntryStatus(models.TextChoices):
    ALLOW = "allow",  "동반 출입 가능"
    DENY = "deny",   "동반 출입 불가능"
    DETAIL = "detail", "상세 입력"


WELCOME_CHOICES = [
    (5, "매우 환영받았어요"),
    (4, "편안했어요"),
    (3, "보통이에요"),
    (2, "조금 어려웠어요"),
    (1, "아쉬워요"),
]


class Footprint(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="footprints")
    place = models.ForeignKey(Place, on_delete=models.CASCADE, related_name="footprints")
    entry_status = models.CharField(max_length=10, choices=EntryStatus.choices)
    entry_detail = models.CharField(max_length=20, blank=True, default="")
    conditions = models.JSONField(default=list, blank=True)

    welcome = models.PositiveSmallIntegerField(choices=WELCOME_CHOICES)

    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "place"], name="uniq_footprint_user_place"),
        ]

    def __str__(self):
        return f"{self.user_id} -> {self.place_id} ({self.entry_status})"