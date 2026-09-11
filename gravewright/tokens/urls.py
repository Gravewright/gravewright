from django.urls import path

from . import views

urlpatterns = [
    path("api/containers/<uuid:campaign_id>/maps/<uuid:map_id>/tokens", views.state)
]
