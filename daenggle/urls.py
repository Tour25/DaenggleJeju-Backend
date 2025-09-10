from django.urls import path
from .views import ShortsListView, RegionShortsView, ConceptShortsView

urlpatterns = [
    path("", ShortsListView.as_view()),
    path("/preference", RegionShortsView.as_view(), name="shorts-region"),
    path("shorts/concepts", ConceptShortsView.as_view(), name="shorts-concepts")
]