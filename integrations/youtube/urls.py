from django.urls import path
from .views import YouTubeSyncView, YouTubeBatchSyncView, TilePresetSyncView

urlpatterns = [
    path("sync", YouTubeSyncView.as_view()),
    path("sync-batch", YouTubeBatchSyncView.as_view()),
    path("sync-real", TilePresetSyncView.as_view())
]
