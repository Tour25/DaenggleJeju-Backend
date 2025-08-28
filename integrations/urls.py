# integrations/urls.py
from django.urls import path, include

app_name = "integrations"

urlpatterns = [

    path("kto/", include(("integrations.kto.urls", "kto"), namespace="kto")),
]
