from django.urls import path
from .views import PlaceMapAllView, PlaceDetailView

urlpatterns = [
    path("map", PlaceMapAllView.as_view(), name="places_map"),
    path("<int:contentId>", PlaceDetailView.as_view()),
]
