from django.urls import path
from .views import PlaceMapAllView, PlaceListView, PlaceDetailView, PlaceDetailFullView, PlaceSearchView, LoadHardcodedView
from .views_extra import PlaceExtraSeedView

urlpatterns = [
    path("map", PlaceMapAllView.as_view(), name="places_map"),
    path("list", PlaceListView.as_view(), name="places-list"),
    path("<int:contentId>", PlaceDetailView.as_view()),
    path("<int:contentId>/full", PlaceDetailFullView.as_view(), name="places_read_full"),
    path("search", PlaceSearchView.as_view(), name="place-search"),
    path("extra-data", LoadHardcodedView.as_view(), name="load-hardcoded"),
    path("extra/seed", PlaceExtraSeedView.as_view(), name="place_extra_seed"),
]
