from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404 # Added
from rest_framework import generics, permissions, status, viewsets 
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import ( # Updated imports
    RegisterSerializer, 
    UserSerializer, 
    AIRobotInstanceSerializer,
    PluginRegistrySerializer, 
    RobotPluginInstanceSerializer
)
from .models import ( # Updated imports
    AIRobotInstance,
    PluginRegistry,
    RobotPluginInstance
)

User = get_user_model()

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (permissions.AllowAny,)
    serializer_class = RegisterSerializer

class UserDetailView(generics.RetrieveUpdateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_object(self):
        return self.request.user

# For Logout - requires simplejwt.token_blacklist app if server-side invalidation is desired
# Ensure 'rest_framework_simplejwt.token_blacklist' is in INSTALLED_APPS
# and run migrations if you use this.
class LogoutView(generics.GenericAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(status=status.HTTP_205_RESET_CONTENT)
        except Exception as e:
            return Response(status=status.HTTP_400_BAD_REQUEST, data={"detail": str(e)})

# You will also use TokenObtainPairView and TokenRefreshView from simplejwt.views
# directly in your urls.py for login and token refresh.
# Example:
# from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
# path('api/auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
# path('api/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

class AIRobotInstanceViewSet(viewsets.ModelViewSet):
    serializer_class = AIRobotInstanceSerializer
    permission_classes = [permissions.IsAuthenticated] # Only authenticated users can manage robots

    def get_queryset(self):
        # Users should only see and manage their own robots
        return AIRobotInstance.objects.filter(owner=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        # Owner is set in the serializer's create method using self.context['request'].user
        # Or, if not done in serializer: serializer.save(owner=self.request.user)
        serializer.save()

    # Optional: Customize other methods like perform_update, perform_destroy if needed.
    # For example, to prevent updating certain fields after creation:
    # def update(self, request, *args, **kwargs):
    #     instance = self.get_object()
    #     # Example: Disallow changing the name after creation
    #     if 'name' in request.data and request.data['name'] != instance.name:
    #         return Response({"detail": "Changing the robot name is not allowed."}, status=status.HTTP_400_BAD_REQUEST)
    #     return super().update(request, *args, **kwargs)

    # Specific actions like /start, /stop for a robot would be added later using @action decorator
    # from rest_framework.decorators import action # Would need this import
    # @action(detail=True, methods=['post'])
    # def start_robot(self, request, pk=None):
    #     robot = self.get_object()
    #     # ... logic to start the robot ...
    #     robot.status = 'ONLINE' # Example
    #     robot.save()
    #     return Response({'status': 'robot starting'})

class PluginRegistryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PluginRegistry.objects.filter(is_approved=True).order_by('name')
    serializer_class = PluginRegistrySerializer
    permission_classes = [permissions.IsAuthenticated]

class RobotPluginInstanceViewSet(viewsets.ModelViewSet):
    serializer_class = RobotPluginInstanceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        robot_pk = self.kwargs.get('robot_pk')
        if not robot_pk:
            # This case should ideally be prevented by URL configuration or return an error
            # For now, returning none to avoid errors if robot_pk is not in URL kwargs
            return RobotPluginInstance.objects.none() 
        
        # Ensure the robot exists and belongs to the requesting user
        robot = get_object_or_404(AIRobotInstance, id=robot_pk, owner=self.request.user)
        return RobotPluginInstance.objects.filter(robot=robot).order_by('plugin_definition__name')

    def perform_create(self, serializer):
        robot_pk = self.kwargs.get('robot_pk')
        # Ensure the robot exists and belongs to the requesting user before creating a plugin instance for it
        robot = get_object_or_404(AIRobotInstance, id=robot_pk, owner=self.request.user)
        # The serializer's context already has the request, so CurrentUserDefault would work for owner
        # However, here we need to associate the plugin with a *specific robot* owned by the user.
        serializer.save(robot=robot)
