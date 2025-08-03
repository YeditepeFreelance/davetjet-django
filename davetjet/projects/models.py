from django.db import models
from invitations.models import Invitation
from recipients.models import Recipient

class Project(models.Model):
  name = models.CharField(max_length=100, unique=True)
  description = models.TextField(blank=True, null=True)

  owner = models.ForeignKey('users.User', related_name='projects', on_delete=models.CASCADE, blank=True, null=True)
  recipients = models.ManyToManyField(Recipient, related_name='project', blank=True)
  invitation = models.ForeignKey(Invitation, related_name='projects', on_delete=models.CASCADE, blank=True, null=True)

  start_date = models.DateField(blank=True, null=True, auto_now_add=True)
  end_date = models.DateField(blank=True, null=True)
  is_active = models.BooleanField(default=True)
  is_archived = models.BooleanField(default=False)


  created_at = models.DateTimeField(auto_now_add=True)
  updated_at = models.DateTimeField(auto_now=True)  

  def __str__(self):
    return self.name

  class Meta:
    verbose_name = "Project"
    verbose_name_plural = "Projects"
    ordering = ['-created_at']