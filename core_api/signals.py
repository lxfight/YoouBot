import uuid
import datetime
from django.conf import settings # Added for settings.USE_TZ
from django.dispatch import Signal, receiver
from django.utils import timezone # For consistent timezone handling if settings.USE_TZ=True
# Import LoggedEvent model after it's defined or from its module
# from .models import LoggedEvent # This will cause circular import if in same app's models.py an import of signals.py happens.
                                # Better to define LoggedEvent in models.py and import here.

# Define the signal
# Arguments that will be sent with this signal
event_published = Signal() 
# Providing arg names for clarity, though Signal() itself doesn't enforce them until send()
# expected_args = ['event_type', 'source_type', 'source_id', 'robot_id', 'user_id', 'visibility', 'payload', 'timestamp']


@receiver(event_published)
def log_event_receiver(sender, **kwargs):
    # Dynamically import here to avoid potential circular imports if models.py imports this file
    # (e.g. if a model method wants to send a signal)
    from .models import LoggedEvent 

    event_type = kwargs.get('event_type')
    source_type = kwargs.get('source_type')
    source_id = kwargs.get('source_id', None)
    robot_id = kwargs.get('robot_id', None)
    user_id = kwargs.get('user_id', None)
    visibility = kwargs.get('visibility', 'INTERNAL')
    payload = kwargs.get('payload', {})
    
    # Use provided timestamp or default to now
    timestamp_provided = kwargs.get('timestamp')
    if isinstance(timestamp_provided, datetime.datetime):
        event_timestamp = timestamp_provided
    elif isinstance(timestamp_provided, str):
        try:
            event_timestamp = datetime.datetime.fromisoformat(timestamp_provided)
        except ValueError:
            event_timestamp = timezone.now() # Fallback
    else:
        event_timestamp = timezone.now() # Default to now if not provided or invalid format

    # Ensure timestamp is timezone-aware if Django project uses timezones
    if settings.USE_TZ and timezone.is_naive(event_timestamp):
        event_timestamp = timezone.make_aware(event_timestamp, timezone.get_default_timezone())


    generated_event_id = uuid.uuid4()

    try:
        LoggedEvent.objects.create(
            event_id=generated_event_id,
            event_type=event_type,
            timestamp=event_timestamp,
            source_type=source_type,
            source_id=source_id,
            robot_id=robot_id,
            user_id=user_id,
            visibility=visibility,
            payload=payload
        )
        print(f"[Event Logged] ID: {generated_event_id}, Type: {event_type}, Source: {source_type}:{source_id}, Robot: {robot_id}, Visibility: {visibility}")
    except Exception as e:
        # Handle database errors or other issues during logging
        print(f"Error logging event {generated_event_id} ({event_type}): {e}")

# To make signals discoverable, they should be imported in the app's AppConfig.ready() method.
# In core_api/apps.py:
# class CoreApiConfig(AppConfig):
#     # ... (existing config) ...
#     def ready(self):
#         import core_api.signals # noqa

def publish_event(sender_component, event_type, source_type, source_id=None, robot_id=None, user_id=None, visibility='INTERNAL', payload=None, timestamp=None):
    if payload is None:
        payload = {}
    
    processed_robot_id = str(robot_id) if robot_id else None
    processed_user_id = str(user_id) if user_id else None
    processed_source_id = str(source_id) if source_id else None

    event_args = {
        'event_type': event_type,
        'source_type': source_type,
        'source_id': processed_source_id,
        'robot_id': processed_robot_id,
        'user_id': processed_user_id,
        'visibility': visibility,
        'payload': payload,
        'timestamp': timestamp,
    }
    
    try:
        event_published.send(sender=sender_component, **event_args)
    except Exception as e:
        print(f"Error during event_published.send for {event_type}: {e}")
