from django.urls import re_path
# We will create consumers.py next
from . import consumers 

websocket_urlpatterns = [
    # Path for WebSocket connections to a specific robot
    # Example: ws://yourserver.com/ws/robot/some_robot_uuid/
    re_path(r'ws/robot/(?P<robot_id>[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})/$', 
            consumers.RobotConsumer.as_asgi()),
    # The regex matches a UUID. Adjust if your robot_id format is different.
]
