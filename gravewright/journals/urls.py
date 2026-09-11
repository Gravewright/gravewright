from django.urls import path
from . import views

urlpatterns = [
    path('api/containers/<uuid:campaign_id>/journal-presentation/<str:ticket>', views.presentation),
    path('game/handouts/presentation/<str:ticket>/asset/<uuid:asset_id>', views.presentation_asset),
    path('api/containers/<uuid:campaign_id>/journals',views.state,name='journal-state'),
    path('game/journal/asset',views.upload,name='journal-upload'),
    path('game/journal/asset/<uuid:asset_id>',views.asset,name='journal-asset'),
]
