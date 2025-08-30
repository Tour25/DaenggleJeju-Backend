from django.urls import path
from .views import YouTubeSyncView

urlpatterns = [
    path("sync", YouTubeSyncView.as_view()),
]
