from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from .models import AIRobotInstance, PluginRegistry, RobotPluginInstance # Updated import

User = get_user_model()

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True, label="Confirm password")
    email = serializers.EmailField(required=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'password2', 'first_name', 'last_name')
        extra_kwargs = {
            'first_name': {'required': False},
            'last_name': {'required': False},
        }

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already exists.")
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', '')
        )
        user.set_password(validated_data['password'])
        user.save()
        return user

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name') # Add other fields as needed
        read_only_fields = ('id', 'username', 'email') # Typically username/email are not changed here

class AIRobotInstanceSerializer(serializers.ModelSerializer):
    owner = UserSerializer(read_only=True) # Display owner details, but don't allow setting via API directly
    # Alternatively, for write operations, you might use:
    # owner = serializers.HiddenField(default=serializers.CurrentUserDefault())
    # This automatically sets the owner to the current authenticated user on create.

    class Meta:
        model = AIRobotInstance
        fields = [
            'id', 
            'owner', 
            'name', 
            'description', 
            'status', 
            'visibility', 
            'created_at', 
            'updated_at', 
            'last_seen_at',
            'version'
        ]
        read_only_fields = ['id', 'owner', 'status', 'created_at', 'updated_at', 'last_seen_at']
        # Status might be updatable via specific actions later, not direct PATCH.
        # Version could also be managed internally.

    def create(self, validated_data):
        # Automatically set the owner to the current authenticated user
        validated_data['owner'] = self.context['request'].user
        return super().create(validated_data)

    # Add any custom validation if needed, for example:
    # def validate_name(self, value):
    #     # Example: Ensure name is not 'admin' or something reserved
    #     if 'admin' in value.lower():
    #         raise serializers.ValidationError("Robot name cannot contain 'admin'.")
    #     return value

class PluginRegistrySerializer(serializers.ModelSerializer):
    class Meta:
        model = PluginRegistry
        fields = [
            'id', 'plugin_id_namespace', 'name', 'description', 'version', 
            'author', 'repository_url', 'manifest_url', 'is_approved',
            'category', 'tags', 'icon_url', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at'] # is_approved might be admin only


class RobotPluginInstanceSerializer(serializers.ModelSerializer):
    plugin_definition = PluginRegistrySerializer(read_only=True) 
    plugin_definition_id = serializers.UUIDField(write_only=True, source='plugin_definition') 
    robot_id = serializers.UUIDField(source='robot.id', read_only=True)

    class Meta:
        model = RobotPluginInstance
        fields = [
            'id', 'robot_id', 'plugin_definition', 'plugin_definition_id', 
            'is_enabled', 'configuration', 'added_at', 'updated_at'
        ]
        read_only_fields = ['id', 'robot_id', 'added_at', 'updated_at', 'plugin_definition']

    def validate_plugin_definition_id(self, value):
        try:
            plugin = PluginRegistry.objects.get(id=value)
            if not plugin.is_approved:
                raise serializers.ValidationError("This plugin is not approved for use.")
        except PluginRegistry.DoesNotExist:
            raise serializers.ValidationError("Plugin with this ID does not exist.")
        return value

    # The 'robot' field for create will be handled in the ViewSet by filtering based on URL or user.
    # def create(self, validated_data):
    #     # Example: robot = self.context['request'].user.robots.get(id=self.context['view'].kwargs['robot_pk'])
    #     # validated_data['robot'] = robot
    #     return super().create(validated_data)
