from django.urls import path
from .views import ShortsListView

urlpatterns = [
    path("shorts", ShortsListView.as_view()),
]