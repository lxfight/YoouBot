from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, AIRobotInstance, PluginRegistry, RobotPluginInstance
import json
from django.utils.safestring import mark_safe

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'first_name', 'last_name', 'is_staff', 'id']
    search_fields = ['username', 'email', 'id']

@admin.register(AIRobotInstance)
class AIRobotInstanceAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'status', 'visibility', 'version', 'created_at', 'id']
    list_filter = ['status', 'visibility', 'owner', 'created_at']
    search_fields = ['name', 'description', 'id', 'owner__username']
    readonly_fields = ['id', 'created_at', 'updated_at', 'last_seen_at']
    fieldsets = (
        (None, {'fields': ('id', 'owner', 'name', 'description')}),
        ('Status and Visibility', {'fields': ('status', 'visibility')}),
        ('Advanced', {'fields': ('version', 'last_seen_at'), 'classes': ('collapse',)}),
        ('Timestamps', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

@admin.register(PluginRegistry)
class PluginRegistryAdmin(admin.ModelAdmin):
    list_display = ['name', 'plugin_id_namespace', 'version', 'category', 'author', 'is_approved', 'created_at']
    list_filter = ['is_approved', 'author', 'category', 'created_at']
    search_fields = ['name', 'plugin_id_namespace', 'description', 'author', 'tags']
    readonly_fields = ['id', 'created_at', 'updated_at']
    fieldsets = (
        (None, {'fields': ('id', 'name', 'plugin_id_namespace', 'version', 'author', 'description')}),
        ('Details & Discovery', {'fields': ('category', 'tags', 'icon_url')}),
        ('Source and Approval', {'fields': ('repository_url', 'manifest_url', 'is_approved')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

@admin.register(RobotPluginInstance)
class RobotPluginInstanceAdmin(admin.ModelAdmin):
    list_display = ('get_robot_name', 'get_plugin_name', 'is_enabled', 'added_at', 'get_updated_at')
    list_filter = ('is_enabled', 'robot__name', 'plugin_definition__name')
    search_fields = ('robot__name', 'plugin_definition__name')
    readonly_fields = ('id', 'added_at', 'updated_at', 'display_configuration', 'display_state')
    fieldsets = (
        (None, {'fields': ('id', 'robot', 'plugin_definition', 'is_enabled')}),
        ('Configuration (Read-Only)', {'fields': ('display_configuration',), 'classes': ('collapse',)}),
        ('State (Read-Only)', {'fields': ('display_state',), 'classes': ('collapse',)}),
        ('Timestamps', {'fields': ('added_at', 'updated_at'), 'classes': ('collapse',)})
    )

    @admin.display(description='Robot', ordering='robot__name')
    def get_robot_name(self, obj):
        return obj.robot.name

    @admin.display(description='Plugin', ordering='plugin_definition__name')
    def get_plugin_name(self, obj):
        return obj.plugin_definition.name

    @admin.display(description='Last Updated', ordering='updated_at')
    def get_updated_at(self, obj):
        return obj.updated_at.strftime("%Y-%m-%d %H:%M:%S")

    def _pretty_json_display(self, data):
        if not data or data == {}: # Check for empty dict
            return "(Empty)"
        pretty = json.dumps(data, indent=4, sort_keys=True)
        return mark_safe(f'<pre style="white-space: pre-wrap; word-break: break-all; max-height: 300px; overflow-y: auto; border: 1px solid #ccc; padding: 5px;">{pretty}</pre>')

    @admin.display(description='Configuration Data')
    def display_configuration(self, obj):
        return self._pretty_json_display(obj.configuration)

    @admin.display(description='State Data')
    def display_state(self, obj):
        return self._pretty_json_display(obj.state)
