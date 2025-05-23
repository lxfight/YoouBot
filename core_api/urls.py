from django.urls import path, include
# Replace DefaultRouter with NestedDefaultRouter
from rest_framework_nested.routers import NestedDefaultRouter, DefaultRouter 
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import (
    RegisterView, 
    UserDetailView, 
    LogoutView,
    AIRobotInstanceViewSet,
    PluginRegistryViewSet,
    RobotPluginInstanceViewSet # Import this ViewSet
)

app_name = 'core_api'

# Main router for top-level resources
router = DefaultRouter()
router.register(r'robots', AIRobotInstanceViewSet, basename='robot')
router.register(r'plugins', PluginRegistryViewSet, basename='plugin') # For browsing available plugins

# Nested router for installed plugins under a specific robot
# This creates URLs like /api/robots/{robot_pk}/installed_plugins/
robots_plugins_router = NestedDefaultRouter(router, r'robots', lookup='robot') 
# 'lookup' should match the URL kwarg that AIRobotInstanceViewSet expects for its detail view,
# and that RobotPluginInstanceViewSet will use to identify the parent robot (e.g. 'robot_pk').
# Our AIRobotInstanceViewSet uses 'pk' by default for its detail view.
# RobotPluginInstanceViewSet's get_queryset uses self.kwargs.get('robot_pk').
# So, the 'lookup' for NestedDefaultRouter should create a kwarg named 'robot_pk'.
# The 'lookup' kwarg for NestedDefaultRouter refers to the lookup field on the parent router.
# So, if parent router for 'robots' uses 'pk', we need to ensure the nested view gets 'robot_pk'.
# The `NestedDefaultRouter` will automatically use `robot_pk` as the kwarg name
# if the parent router's lookup is `pk` and the parent resource is `robots`.

robots_plugins_router.register(
    r'installed_plugins', 
    RobotPluginInstanceViewSet, 
    basename='robot-installed-plugins' # Basename for the nested route
)
# This will generate URLs like:
# /robots/{robot_pk}/installed_plugins/ [GET, POST]
# /robots/{robot_pk}/installed_plugins/{pk}/ [GET, PUT, PATCH, DELETE]


auth_urlpatterns = [
    path('auth/register/', RegisterView.as_view(), name='auth_register'),
    path('auth/login/', TokenObtainPairView.as_view(), name='auth_login'),
    path('auth/login/refresh/', TokenRefreshView.as_view(), name='auth_token_refresh'),
    path('auth/logout/', LogoutView.as_view(), name='auth_logout'),
    path('users/me/', UserDetailView.as_view(), name='user_me'),
]

urlpatterns = auth_urlpatterns + [
    path('', include(router.urls)),
    path('', include(robots_plugins_router.urls)), # Add nested router URLs
]
