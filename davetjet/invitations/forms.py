from django import forms
from .models import Invitation

class InvitationForm(forms.ModelForm):
  class Meta:
    model = Invitation
    fields = ['name', 'project', 'message', 'recipients', 'channels', 'reminders', 'invitation_date']
    widgets = {
      'recipients': forms.CheckboxSelectMultiple,
      'project': forms.Select(attrs={'class': 'form-control'}),
      'name': forms.TextInput(attrs={'class': 'form-control'}),
      'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
      'channels': forms.Select(attrs={'class': 'form-control'}),
      'reminders': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
      'invitation_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
    }