from django.urls import path
from .views import RegionShortsView, ConceptShortsView, RegionPlainShortsView, TrendingShortsView, AccommodationShortsView, ShortsSearchView, PlaceDaenggleRecommendView

urlpatterns = [
    path("/trending",TrendingShortsView.as_view()),
    path("/accommodations", AccommodationShortsView.as_view()),
    path("/regions", RegionPlainShortsView.as_view()),
    path("/preference", RegionShortsView.as_view(), name="shorts-region"),
    path("/concepts", ConceptShortsView.as_view(), name="shorts-concepts"),
    path("/search", ShortsSearchView.as_view(), name="shorts-search"),
    path("/places/<int:contentId>/recommendations", PlaceDaenggleRecommendView.as_view(), name="shorts-recommendations")
]