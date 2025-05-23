import json
import datetime # For timestamp
import uuid # For UUID casting
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async # For accessing Django ORM
from django.contrib.auth import get_user_model
from .models import AIRobotInstance # Assuming your robot model is here
from .signals import publish_event # Import the helper function

User = get_user_model()

class RobotConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.robot_id = self.scope['url_route']['kwargs']['robot_id']
        self.robot_group_name = f'robot_{self.robot_id}'
        
        # Get the user from the scope (populated by AuthMiddlewareStack)
        self.user = self.scope.get('user')

        if not self.user or not self.user.is_authenticated:
            # Reject connection if user is not authenticated
            await self.close()
            return

        # Check if the authenticated user has access to this robot
        # This requires an async database call
        if not await self.user_has_access_to_robot(self.user, self.robot_id):
            await self.close()
            return

        # Join robot-specific group
        await self.channel_layer.group_add(
            self.robot_group_name,
            self.channel_name
        )
        await self.accept()
        print(f"WebSocket connected for robot {self.robot_id}, user {self.user.username}, channel {self.channel_name}")

        # Send a connection confirmation message to the client
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': f'Successfully connected to robot {self.robot_id}'
        }))


    async def disconnect(self, close_code):
        # Leave robot-specific group
        if hasattr(self, 'robot_group_name'): # Check if attribute exists, in case connect failed early
            await self.channel_layer.group_discard(
                self.robot_group_name,
                self.channel_name
            )
        print(f"WebSocket disconnected for robot {self.robot_id}, user {self.user.username if hasattr(self, 'user') and self.user else 'Unknown'}, channel {self.channel_name}")

    # Helper method to check robot access (must be async for DB operations)
    @database_sync_to_async
    def user_has_access_to_robot(self, user, robot_id_str): # Renamed to robot_id_str for clarity
        try:
            # Convert string robot_id from URL to UUID object for query
            robot_uuid = uuid.UUID(robot_id_str)
            robot = AIRobotInstance.objects.get(id=robot_uuid, owner=user)
            return True
        except AIRobotInstance.DoesNotExist:
            print(f"User {user.username} does not have access to robot {robot_id_str} or robot does not exist.")
            return False
        except ValueError: # Handle invalid UUID format for robot_id
             print(f"Invalid UUID format for robot_id: {robot_id_str}")
             return False

    # Receive message from WebSocket client
    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            payload = data.get('payload', {})
            
            print(f"Received message type '{message_type}' from {self.user.username} for robot {self.robot_id}: {payload}")

            if message_type == 'chat_message_to_robot':
                text = payload.get('text')
                if text:
                    # Broadcast this message to the robot's group
                    await self.broadcast_chat_message(text)
                else:
                    await self.send_error_message("Missing 'text' in payload for chat_message_to_robot.")
            # Add handlers for other message types from client here if needed
            # e.g., plugin_action, command_to_robot
            else:
                await self.send_error_message(f"Unknown message type: {message_type}")

        except json.JSONDecodeError:
            await self.send_error_message("Invalid JSON received.")
        except Exception as e:
            await self.send_error_message(f"Error processing message: {str(e)}")

    async def broadcast_chat_message(self, received_text):
        timestamp_obj = datetime.datetime.now(datetime.timezone.utc)
        timestamp_iso = timestamp_obj.isoformat()

        message_payload_for_client = {
            'sender_username': self.user.username,
            'text': received_text,
            'robot_id': self.robot_id, # This is already a string from the URL
            'timestamp': timestamp_iso,
        }
        
        message_to_broadcast_to_group = {
            'type': 'chat_message_handler', # This 'type' is for the group_send internal dispatch
            'message_content': { # This is the actual content to be sent to clients
                'type': 'chat_message_from_robot', # This 'type' is for client-side parsing
                'payload': message_payload_for_client
            }
        }
        await self.channel_layer.group_send(
            self.robot_group_name,
            message_to_broadcast_to_group
        )
        print(f"Broadcasted message from {self.user.username} to group {self.robot_group_name}")

        # *** NEW: Publish an event ***
        try:
            publish_event(
                sender_component=self, # The consumer instance
                event_type='chat.Message.Broadcasted',
                source_type='USER_CLIENT', 
                source_id=str(self.user.id) if self.user else None,
                robot_id=self.robot_id, # Already a UUID string from URL route
                user_id=str(self.user.id) if self.user else None, 
                visibility='USER_VISIBLE', 
                payload=message_payload_for_client, 
                timestamp=timestamp_obj # Pass the datetime object
            )
        except Exception as e:
            print(f"Error publishing chat.Message.Broadcasted event: {e}")


    # Handler for messages dispatched from group_send
    async def chat_message_handler(self, event):
        # This method name 'chat_message_handler' MUST match the 'type' in group_send
        message_content = event['message_content']
        
        # Send the message content to the WebSocket client
        await self.send(text_data=json.dumps(message_content))
        print(f"Sent message to client {self.channel_name} in group {self.robot_group_name}: {message_content}")

    # Handler for robot status update messages dispatched from group_send
    async def robot_status_update_handler(self, event):
        # This method name MUST match the 'type' in group_send from other parts of the app
        status_details = event['status_details'] # Expecting this key in the event
        
        # Construct the message to send to the client
        message_to_send = {
            'type': 'robot_status_update', # This 'type' is for client-side parsing
            'payload': {
                'robot_id': status_details.get('robot_id', self.robot_id), # robot_id from event or consumer
                'status': status_details.get('status'),
                'message': status_details.get('message', ''), # Optional message
                'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            }
        }
        
        await self.send(text_data=json.dumps(message_to_send))
        print(f"Sent robot status update to client {self.channel_name} for robot {self.robot_id}: {message_to_send['payload']}")

    async def send_error_message(self, error_text):
        await self.send(text_data=json.dumps({
            'type': 'error_message',
            'payload': {
                'message': error_text,
                'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            }
        }))
        print(f"Sent error to client {self.channel_name}: {error_text}")
