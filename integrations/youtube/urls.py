from django.urls import path
from .views import YouTubeSyncView, YouTubeBatchSyncView

urlpatterns = [
    path("sync", YouTubeSyncView.as_view()),
    path("sync-batch", YouTubeBatchSyncView.as_view()),
]
