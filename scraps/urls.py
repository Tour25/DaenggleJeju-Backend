from django.urls import path
from .views import ScrapView, ScrapListView

urlpatterns = [
    path("", ScrapView.as_view()),
    path("/my", ScrapListView.as_view()),
]