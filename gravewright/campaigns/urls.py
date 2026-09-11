from django.urls import path
from . import views, streamer

app_name = 'campaigns'
urlpatterns = [
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
