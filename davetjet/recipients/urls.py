from django.urls import path
from .views import RecipientTestView, CreateRecipientView, AddFromFileView

app_name = 'recipients'

urlpatterns = [
  path('test', RecipientTestView.as_view(), name='test'),
  path('add-new', CreateRecipientView.as_view(), name='add_new'),
  path('add-from-file', AddFromFileView.as_view(), name='add_from_file'),
]