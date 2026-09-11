from django.urls import path
from . import views, media
from gravewright.chat.card_attachments import media as chat_card_media

app_name = 'table'
urlpatterns = [path('game/<uuid:campaign_id>/chat', views.table, {'detached_chat': True}, name='chat-window'), path('game/<uuid:campaign_id>', views.table, name='workspace')]

urlpatterns += [
    path("game/chat/<int:message_id>/cards/<int:attachment_id>/<str:face>", chat_card_media),
    path('api/containers/<uuid:campaign_id>/permissions-members', views.permission_members),
    path('api/containers/<uuid:campaign_id>/modules-native/<str:module>', views.module_state),
    path('api/containers/<uuid:campaign_id>/media/<str:kind>', media.upload),
    path('game/audio/<uuid:track_id>', media.audio_file),
    path('game/cards/<str:kind>/<uuid:object_id>/<str:face>', media.card_file),
]
