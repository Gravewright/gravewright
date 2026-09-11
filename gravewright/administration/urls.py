from django.urls import path

from . import views

urlpatterns = [
    path("api/admin/settings", views.preferences),
    path("api/admin/settings/<str:section>", views.update_preferences),
    path("api/privacy", views.public_privacy),
    path("api/admin/status", views.status),
    path("api/admin/diagnostics", views.diagnostics),
    path("api/admin/updates/<str:action>", views.updates),
    path("api/admin/campaigns/import", views.import_campaign),
    path("api/admin/campaigns/<uuid:campaign_id>/clone/<str:action>", views.clone),
    path("api/containers/<uuid:campaign_id>/export", views.export_campaign),
    path("api/containers/<uuid:campaign_id>/snapshots", views.snapshots),
    path(
        "api/containers/<uuid:campaign_id>/snapshots/<uuid:snapshot_id>/<str:action>",
        views.snapshot_action,
    ),
]
