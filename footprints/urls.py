from django.urls import path
from .views import FootprintCreateView, MyFootprintsListView, PlaceFootprintsListView

urlpatterns = [
    path("", FootprintCreateView.as_view(), name="footprints_create"),
    path("/my", MyFootprintsListView.as_view(), name="footprints_my"),
    path("/places/<int:contentId>", PlaceFootprintsListView.as_view(), name="footprints_place_list"),
]