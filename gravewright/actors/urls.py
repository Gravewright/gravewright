from django.urls import path

from . import views

urlpatterns = [
    path("api/containers/<uuid:campaign_id>/actors", views.state),
    path("api/containers/<uuid:campaign_id>/actors/<uuid:actor_id>/sheet", views.sheet),
    path("api/containers/<uuid:campaign_id>/actor-upload", views.upload),
    path("game/actors/asset/<uuid:asset_id>", views.asset),
]
