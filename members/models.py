from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.utils import timezone
from django.conf import settings

class UserManager(BaseUserManager):
    def create_user(self, handle: str, password=None, **extra):
        if not handle:
            raise ValueError("handle is required")
        user = self.model(handle=handle, **extra)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password() 
        user.save(using=self._db)
        return user

    def create_superuser(self, handle: str, password, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        if not password:
            raise ValueError("Superuser must have a password")
        return self.create_user(handle, password, **extra)

class User(AbstractBaseUser, PermissionsMixin):

    handle = models.CharField(max_length=40, unique=True)  # 예: "kakao_123456789"

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    USERNAME_FIELD = "handle"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.handle


class MemberPreference(models.Model):

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="preference",
    )

    region_context_ids = models.JSONField(default=list)

    style_codes = models.JSONField(default=list)

    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "member_preference"

    def __str__(self):
        return f"{self.user_id} / regions={len(self.region_context_ids)} / styles={self.style_codes}"

