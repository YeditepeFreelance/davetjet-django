from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
app_name = 'davetjet'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('payments/', include('payments.urls', namespace='payments')),
    path('projects/', include('projects.urls', namespace='projects')),
    path('recipients/', include('recipients.urls', namespace='recipients')),
    path('invitations/', include('invitations.urls', namespace='invitations')),
    path('', include('core.urls', namespace='core')),
    # Token 
    
    # API namespaces
    # path('api/users/', include('users.urls')),
    # path('api/payments/', include('payments.urls')),
    # path('api/events/', include('events.urls')),
    # path('api/invitations/', include('invitations.urls')),

]
