from django.urls import path
from .views import ScriptView, AskView

urlpatterns = [
    path("script", ScriptView.as_view()),
    path("ask", AskView.as_view()),
]