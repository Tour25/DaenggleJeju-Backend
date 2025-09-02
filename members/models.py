from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.utils import timezone

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
