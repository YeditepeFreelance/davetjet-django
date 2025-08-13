# recipients/models.py
from django.db import models

RSVP_STATUS = [
        ('pending', 'Beklemede'),
        ('yes', 'Geliyor'),
        ('maybe', 'Emin Değil'),
        ('no', 'Gelmiyor'),
    ]
class Recipient(models.Model):
    name = models.CharField(max_length=100, unique=False)
    email = models.EmailField(unique=False)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)

    rsvp_status = models.CharField(
        max_length=10,
        choices=RSVP_STATUS,
        default='pending'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property 
    def rsvp(self):
        return self.get_rsvp_status_display()
    def __str__(self):
        return self.name
