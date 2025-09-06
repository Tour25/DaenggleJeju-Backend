from django.urls import path
from .views import MemberPreferenceUpsertView

urlpatterns = [
    path("preference", MemberPreferenceUpsertView.as_view(), name="member-preference-upsert"),
]