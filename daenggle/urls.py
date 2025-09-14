from django.urls import path
from .views import RegionShortsView, ConceptShortsView, RegionPlainShortsView, TrendingShortsView, AccommodationShortsView

urlpatterns = [
    path("/shorts/trending",TrendingShortsView.as_view()),
    path("/shorts/accommodations", AccommodationShortsView.as_view()),
    path("/shorts/regions", RegionPlainShortsView.as_view()),
    path("/preference", RegionShortsView.as_view(), name="shorts-region"),
    path("shorts/concepts", ConceptShortsView.as_view(), name="shorts-concepts")
]