from django.db import models
from django.conf import settings
from datetime import date

class PetBreed(models.Model):
    code = models.SlugField(max_length=64, unique=True)
    name_ko = models.CharField(max_length=100)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "pets_dog_breed"
        ordering = ["name_ko"]

    def __str__(self):
        return f"{self.name_ko} ({self.code})"


class PetProfile(models.Model):

    class Size(models.TextChoices):
        SMALL = "SMALL", "소형견(10kg 미만)"
        MEDIUM = "MEDIUM", "중형견(6~15kg)"
        LARGE = "LARGE", "대형견(16~30kg)"
        XLARGE="XLARGE", "초대형견(30kg 이상)"


    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="dogs")
    name = models.CharField(max_length=50, help_text="반려견 이름")
    breed = models.ForeignKey(PetBreed, null=True, blank=True, on_delete=models.SET_NULL, related_name="dogs")

    size_code = models.CharField(max_length=10, choices=Size.choices)

    birth_date = models.DateField(null=True, blank=True, help_text="생년월일(YYYY-MM-DD)")

    class Meta:
        db_table = "pets_dog_profile"
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["size_code"]),
            models.Index(fields=["breed"]),
        ]
        ordering = ["-id"]

    def __str__(self):
        return f"{self.name} / {self.user_id}"

    @property
    def age_years(self):
        if not self.birth_date:
            return None
        today = date.today()
        return max(0, today.year - self.birth_date.year -
                   ((today.month, today.day) < (self.birth_date.month, self.birth_date.day)))
