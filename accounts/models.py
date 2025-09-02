from django.conf import settings
from django.db import models

class SocialAccount(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="socialaccounts")
    provider = models.CharField(max_length=20)         # Kakao
    provider_user_id = models.CharField(max_length=64)  # Kakao id

    class Meta:
        unique_together = ("provider", "provider_user_id")
