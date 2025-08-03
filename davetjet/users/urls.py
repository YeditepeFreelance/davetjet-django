from django.urls import path
from .views import CustomLoginView
from . import views

app_name = 'users'

urlpatterns = [
    path('ajax/check-username/', views.check_username, name='check_username'),
    path('ajax/check-email/', views.check_email, name='check_email'),
    path('ajax/check-password/', views.check_password, name='check_password'),
    # path('login/', CustomLoginView.as_view(), name='login'),
]
