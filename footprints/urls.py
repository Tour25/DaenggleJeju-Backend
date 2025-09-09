from django.urls import path
from .views import FootprintCreateView, MyFootprintsListView

urlpatterns = [
    path("", FootprintCreateView.as_view(), name="footprints_create"),
    path("/my", MyFootprintsListView.as_view(), name="footprints_my"),
]