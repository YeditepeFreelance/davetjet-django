from django.urls import path
from .views import UserListView, UserDetailView, ProfileDetailView, UserCreateView, UserDeleteView, UserUpdateView

urlpatterns = [
    path('', UserListView.as_view(), name='user-list'),
    path('<int:pk>/', UserDetailView.as_view(), name='user-detail'),
    path('profiles/<int:pk>/', ProfileDetailView.as_view(), name='profile-detail'),
        path('create/', UserCreateView.as_view(), name='user-create'),
    path('delete/<int:pk>/', UserDeleteView.as_view(), name='user-delete'),
        path('update/<int:pk>/', UserUpdateView.as_view(), name='user-update'),


]
