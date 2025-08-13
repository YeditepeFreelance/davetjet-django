from django.urls import path
from .views import CreateRecipientView, ExportRecipientsView, ImportRecipientsView, EditRecipientView, DeleteRecipientView, RecipientQuotaView, recipient_autocomplete, recipients_handler, rsvp_update

app_name = 'recipients'

urlpatterns = [
  path('add-new', CreateRecipientView.as_view(), name='add_new'),

  path('export-csv', ExportRecipientsView.as_view(), name='export-csv'),
  path('import-csv', ImportRecipientsView.as_view(), name='import-csv'),
  path('edit', EditRecipientView.as_view(), name='edit'),
  path('delete/<int:pk>/', DeleteRecipientView.as_view(), name='delete'),
  path('autocomplete/', recipient_autocomplete, name='recipient_autocomplete'),
    path("quota/", RecipientQuotaView.as_view(), name="recipient-quota"),

  path('rsvp/', rsvp_update, name='rsvp_update'),
  path('<slug:invitation_slug>/', recipients_handler, name='recipients_handler'),


]