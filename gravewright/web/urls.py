from django.urls import path
from . import inside

app_name = 'web'
urlpatterns = [
    path('inside', inside.inside, name='inside'),
    path('inside/', inside.inside),
    path('inside/dialog/<str:mode>', inside.dialog, name='dialog'),
    path('inside/dialog/<str:mode>/<uuid:campaign_id>', inside.dialog, name='campaign-dialog'),
    path('inside/campaigns/create', inside.save_campaign, name='create'),
    path('inside/campaigns/<uuid:campaign_id>/edit', inside.save_campaign, name='edit'),
    path('inside/campaigns/<uuid:campaign_id>/invite', inside.issue_code, {'kind': 'invite'}, name='invite'),
    path('inside/campaigns/<uuid:campaign_id>/removal-code', inside.issue_code, {'kind': 'remove'}, name='removal-code'),
    path('inside/campaigns/<uuid:campaign_id>/remove', inside.remove, name='remove'),
    path('inside/campaigns/join', inside.join, name='join'),
    path('inside/account', inside.save_account, name='account'),
    path('api/player-preferences', inside.preferences, name='preferences'),
]
