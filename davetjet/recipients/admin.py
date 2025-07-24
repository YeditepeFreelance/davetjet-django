from django.contrib import admin
from .models import Recipient

@admin.register(Recipient)
class RecipientAdmin(admin.ModelAdmin):
    list_display = ('name', 'email')
    search_fields = ('name', 'email')
    ordering = ('-id',)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related()