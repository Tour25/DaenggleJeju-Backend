from django.urls import path
from .views import PetBreedInitView, PetBreedSearchView, PetProfileCreateView

urlpatterns = [
    path("breeds/init", PetBreedInitView.as_view()),
    path("breeds/search", PetBreedSearchView.as_view()),
    path("profiles", PetProfileCreateView.as_view(), name="pet-profile-create"),
]
