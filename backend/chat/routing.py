from django.urls import re_path

from . import consumers

print("Routing loaded")

websocket_urlpatterns = [
    #re_path(r'ws/chat/(?P<room_name>\w+)/$', consumers.ChatConsumer.as_asgi()),
    re_path(r'ws/chat/(?P<user_id>\d+)/(?P<other_user_id>\d+)/$', consumers.PrivateChatConsumer.as_asgi()),
    re_path(r'ws/notifications/(?P<user_id>\d+)/$', consumers.NotificationConsumer.as_asgi()),
    re_path(r'ws/presence/(?P<user_id>\d+)/$', consumers.PresenceConsumer.as_asgi()),
]