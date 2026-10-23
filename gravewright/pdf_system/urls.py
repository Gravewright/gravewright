from django.urls import path

from . import views

urlpatterns = [
    path("api/containers/<uuid:campaign_id>/pdf-mappings", views.library),
    path("api/containers/<uuid:campaign_id>/pdf-mappings/<uuid:template_id>/export", views.export),
]
