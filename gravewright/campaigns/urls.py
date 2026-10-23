from django.urls import path
from . import views, streamer, management_views

app_name = 'campaigns'
urlpatterns = [
    path('campaigns/<uuid:campaign_id>/manage', management_views.page, name='manage'),
    path('api/containers/<uuid:campaign_id>/management', management_views.overview, name='management'),
    path('api/containers/<uuid:campaign_id>/preparation', management_views.preparation, name='preparation'),
    path('api/containers/<uuid:campaign_id>/references', management_views.references, name='references'),
    path('api/containers/<uuid:campaign_id>/view-as/<uuid:user_id>', management_views.view_as, name='view-as'),
    path('api/containers/<uuid:campaign_id>/journal-history/<uuid:journal_id>', management_views.journal_history, name='journal-history'),
    path('api/containers/<uuid:campaign_id>/journal-revisions/<uuid:revision_id>', management_views.journal_revision, name='journal-revision'),
    path('api/containers/<uuid:campaign_id>/journal-trash', management_views.journal_trash, name='journal-trash'),
    path('stream/<str:token>', streamer.consume),
    path('api/containers/<uuid:campaign_id>/streamer-link', views.streamer_link),
    path('api/containers/<uuid:campaign_id>/streamer-link/revoke', views.revoke_streamer),
    path('api/containers/<uuid:campaign_id>/onboarding', views.onboarding),
    path('api/containers/<uuid:campaign_id>/onboarding/claim', views.player_onboarding),
    path('api/containers/<uuid:campaign_id>/members/ban', views.ban_member),
    path('api/containers', views.containers),
    path('api/containers/join', views.join),
    path('api/containers/<uuid:campaign_id>', views.update),
    path('api/containers/<uuid:campaign_id>/invitation', views.code, {'kind': 'invite'}),
    path('api/containers/<uuid:campaign_id>/removal-code', views.code, {'kind': 'remove'}),
    path('api/containers/<uuid:campaign_id>/remove', views.remove),
    path('api/containers/<uuid:campaign_id>/invitation/status', views.invitation_status),
    path('api/containers/<uuid:campaign_id>/invitation/revoke', views.revoke_invitation_code),
    path('api/rulesets', views.rulesets),
    path('campaigns/<uuid:campaign_id>/cover', views.cover, name='cover'),
]
