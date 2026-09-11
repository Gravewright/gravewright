from django.urls import path

from . import views, frontend

urlpatterns = [
    path("api/tables/<uuid:table_id>/api", frontend.call),
    path("api/tables/<uuid:table_id>/modules/<str:module_id>/api", frontend.call),
    path("api/marketplace/status", views.marketplace_status),
    path("api/marketplace", views.marketplace),
    path("api/marketplace/install", views.install),
    path("api/module-packages", views.installed),
    path(
        "api/module-packages/<str:module_id>/<str:version>/<str:digest>/<path:asset>",
        views.asset,
    ),
    path("api/tables/<uuid:table_id>/modules", views.state),
    path("api/tables/<uuid:table_id>/modules/ack", views.acknowledge),
    path("api/tables/<uuid:table_id>/modules/<str:module_id>/context", views.context),
    path("api/tables/<uuid:table_id>/modules/<str:module_id>/storage", views.storage),
    path("api/tables/<uuid:table_id>/modules/<str:module_id>/call", views.call),
]
