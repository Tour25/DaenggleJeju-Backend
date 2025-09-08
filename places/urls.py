from django.urls import path
from .views import PlaceMapAllView, PlaceListView, PlaceDetailView, PlaceDetailFullView

urlpatterns = [
    path("map", PlaceMapAllView.as_view(), name="places_map"),
    path("list", PlaceListView.as_view(), name="places-list"),
    path("<int:contentId>", PlaceDetailView.as_view()),
    path("places/<int:contentId>/full", PlaceDetailFullView.as_view(), name="places_read_full"),
]
