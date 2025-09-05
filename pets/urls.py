from django.urls import path
from .views import PetBreedInitView, PetBreedSearchView

urlpatterns = [
    path("breeds/init", PetBreedInitView.as_view()),
    path("breeds/search", PetBreedSearchView.as_view()),
]
