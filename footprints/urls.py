from django.urls import path
from .views import FootprintCreateView, MyFootprintsListView, PlaceFootprintsListView
from .views_dummy import DummyFootprintSeedView

urlpatterns = [
    path("", FootprintCreateView.as_view(), name="footprints_create"),
    path("/my", MyFootprintsListView.as_view(), name="footprints_my"),
    path("/places/<int:contentId>", PlaceFootprintsListView.as_view(), name="footprints_place_list"),
    path("/dummy/seed", DummyFootprintSeedView.as_view()),

]