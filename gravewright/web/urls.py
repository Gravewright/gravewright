from django.urls import path
from django.views.generic import RedirectView
from . import inside

app_name = 'web'
urlpatterns = [
    path("favicon.ico", RedirectView.as_view(url="/static/gravewright_web/favicon.svg")),
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
    path('inside/language', inside.language, name='language'),
    path('api/player-preferences', inside.preferences, name='preferences'),
]
