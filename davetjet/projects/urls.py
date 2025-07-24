from django.urls import path 
from .views import ProjectsTestView, CreateProjectView

app_name = 'projects'

urlpatterns = [
  path('test', ProjectsTestView.as_view(), name='test'),
  path('create', CreateProjectView.as_view(), name='create'),
]