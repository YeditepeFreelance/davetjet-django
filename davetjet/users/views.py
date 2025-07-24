from rest_framework import generics, permissions
from rest_framework_api_key.permissions import HasAPIKey
from django.contrib.auth import get_user_model
from .models import Profile
from .serializers import UserSerializer, ProfileSerializer

User = get_user_model()

# 🔹 User List — restricted to API key holders only (or admins if you combine)
class UserListView(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [HasAPIKey]  # or combine with others

# 🔹 User Detail — allow either authenticated user OR API key
class UserDetailView(generics.RetrieveUpdateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [HasAPIKey]

# 🔹 Profile Detail — allow either authenticated user OR API key
class ProfileDetailView(generics.RetrieveUpdateAPIView):
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
    permission_classes = [HasAPIKey]

class UserCreateView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [HasAPIKey]  # or IsAdminUser if you prefer

# 🔹 Delete User
class UserDeleteView(generics.DestroyAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [HasAPIKey]  # or IsAdminUser
    lookup_field = 'pk'  # default

class UserUpdateView(generics.RetrieveUpdateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [HasAPIKey]
    lookup_field = 'pk'  # So you can use /update/3/