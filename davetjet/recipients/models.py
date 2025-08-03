from django.db import models

class Recipient(models.Model):
    name = models.CharField(max_length=100, unique=False)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Recipient"
        verbose_name_plural = "Recipients"
        ordering = ['name']