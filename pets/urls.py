from django.urls import path
from .views import PetBreedInitView, PetBreedSearchView, PetProfileCreateView, PetProfileUpdateView, PetProfileView, PetProfileListView

urlpatterns = [
    path("breeds/init", PetBreedInitView.as_view()),
    path("breeds/search", PetBreedSearchView.as_view()),
    path("profiles", PetProfileCreateView.as_view(), name="pet-profile-create"),
    path("profiles-list", PetProfileListView.as_view(), name="petprofile_list"),
    path("profiles/<int:petId>", PetProfileView.as_view(), name="pet-profile-my"),
    path("profiles/<int:petId>/edit", PetProfileUpdateView.as_view(), name="pets_profiles_edit_partial_update")

]
