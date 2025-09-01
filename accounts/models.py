from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()

class SocialAccount(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="socialaccounts")
    provider = models.CharField(max_length=20)         # Kakao
    provider_user_id = models.CharField(max_length=64)  # Kakao id

    class Meta:
        unique_together = ("provider", "provider_user_id")
