from django.urls import path
from . import views, assets

urlpatterns = [
    path('api/containers/<uuid:campaign_id>/library/asset-state', assets.state),
    path('api/containers/<uuid:campaign_id>/library/upload', assets.upload),
    path('api/containers/<uuid:campaign_id>/library/assets/<str:action>', assets.command),
    path('game/map-assets/<uuid:asset_id>', assets.file),
    path("api/maps/<uuid:map_id>/tiles/<int:lod>/<int:x>/<int:y>.webp", views.tile),
    path("api/containers/<uuid:campaign_id>/scene-upload", views.upload),
    path("api/containers/<uuid:campaign_id>/scenes", views.state),
    path("api/maps/<uuid:map_id>/state", views.layers),
    path("api/maps/<uuid:map_id>/manifest", views.manifest),
    path("api/maps/<uuid:map_id>/tiles/<int:lod>/<int:x>/<int:y>", views.tile),
]
