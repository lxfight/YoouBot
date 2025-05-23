import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Add any additional user-specific fields here later, e.g.:
    # avatar_url = models.URLField(blank=True, null=True)
    # preferences = models.JSONField(default=dict)

    def __str__(self):
        return self.username

class AIRobotInstance(models.Model):
    STATUS_CHOICES = [
        ('OFFLINE', 'Offline'),
        ('ONLINE', 'Online'),
        ('TRAINING', 'Training'),
        ('ERROR', 'Error'),
        ('MAINTENANCE', 'Maintenance'),
    ]

    VISIBILITY_CHOICES = [
        ('PRIVATE', 'Private'),
        ('SHARED', 'Shared'), # Actual sharing mechanism to be defined later
        ('PUBLIC', 'Public'),   # Actual public access to be defined later
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='robots')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OFFLINE')
    visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default='PRIVATE')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_seen_at = models.DateTimeField(blank=True, null=True)

    version = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.name} (Owner: {self.owner.username})"

    class Meta:
        ordering = ['-created_at']
        unique_together = [['owner', 'name']]

class PluginRegistry(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plugin_id_namespace = models.CharField(max_length=255, unique=True, help_text="Unique identifier string for the plugin, e.g., 'com.community.weather_plugin'")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    version = models.CharField(max_length=50) # e.g., "1.0.2"
    author = models.CharField(max_length=255, blank=True)
    repository_url = models.URLField(blank=True, null=True)
    manifest_url = models.URLField(blank=True, null=True, help_text="URL to the plugin's manifest file if hosted externally")
    is_approved = models.BooleanField(default=False, help_text="Whether the plugin is approved for use on this platform")
    
    # New fields for PluginRegistry
    category = models.CharField(max_length=100, blank=True, help_text="Plugin category, e.g., 'Utilities', 'AI Enhancement', 'IoT'")
    tags = models.CharField(max_length=255, blank=True, help_text="Comma-separated tags for discoverability")
    icon_url = models.URLField(blank=True, null=True, help_text="URL to an icon for the plugin")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} v{self.version} ({self.plugin_id_namespace})"

    class Meta:
        verbose_name_plural = "Plugin Registry Entries"
        ordering = ['name', 'version'] # Corrected ordering, version often sorted ascending for display

class RobotPluginInstance(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    robot = models.ForeignKey(AIRobotInstance, on_delete=models.CASCADE, related_name='plugin_instances')
    plugin_definition = models.ForeignKey(PluginRegistry, on_delete=models.CASCADE, related_name='robot_instances')
    is_enabled = models.BooleanField(default=True)
    # Stores plugin-specific configuration provided by the user for this robot instance
    # e.g., API keys, location settings for a weather plugin, etc.
    configuration = models.JSONField(default=dict, blank=True, help_text="User-specific configuration for this plugin on this robot.")
    # Stores plugin-specific state that needs to persist for this robot instance (optional)
    # e.g., last run time, learned user preferences for this plugin on this robot.
    state = models.JSONField(default=dict, blank=True, help_text="Persistent state for this plugin on this robot.")
    
    added_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [['robot', 'plugin_definition']] # A robot can only have one instance of each plugin definition
        ordering = ['robot', 'plugin_definition__name']

    def __str__(self):
        return f"{self.plugin_definition.name} on {self.robot.name} ({'Enabled' if self.is_enabled else 'Disabled'})"

class LoggedEvent(models.Model):
    VISIBILITY_CHOICES = [
        ('INTERNAL', 'Internal System Event'),
        ('USER_VISIBLE', 'Visible to User Clients'),
        ('PLUGIN_VISIBLE', 'Visible to Plugins'),
        # Add more if needed
    ]
    SOURCE_TYPE_CHOICES = [
        ('SYSTEM', 'System'),
        ('USER_CLIENT', 'User Client'),
        ('ROBOT_CORE', 'Robot Core Logic'), # From the AIRobotInstance itself
        ('PLUGIN', 'Plugin'),
        # Add more as system evolves
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_id = models.UUIDField(unique=True, editable=False) # Will be set by the signal receiver
    event_type = models.CharField(max_length=255, db_index=True, help_text="e.g., 'robot.StatusChanged', 'chat.Message.Sent'")
    timestamp = models.DateTimeField(db_index=True, help_text="Timestamp of when the event occurred or was processed")
    
    source_type = models.CharField(max_length=50, choices=SOURCE_TYPE_CHOICES, db_index=True)
    source_id = models.CharField(max_length=255, blank=True, null=True, help_text="Identifier of the source (e.g., user_id, plugin_id, session_id)")
    
    robot_id = models.UUIDField(null=True, blank=True, db_index=True, help_text="Associated robot instance, if any")
    user_id = models.UUIDField(null=True, blank=True, db_index=True, help_text="Associated user, if any")
    
    visibility = models.CharField(max_length=50, choices=VISIBILITY_CHOICES, default='INTERNAL')
    payload = models.JSONField(default=dict, blank=True, help_text="Arbitrary data specific to the event type")

    created_at = models.DateTimeField(auto_now_add=True, help_text="Timestamp of when the event was logged") # Log time

    class Meta:
        ordering = ['-timestamp'] # Order by when event happened, then by log time
        verbose_name = "Logged Event"
        verbose_name_plural = "Logged Events"

    def __str__(self):
        return f"{self.event_type} ({self.event_id}) at {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
