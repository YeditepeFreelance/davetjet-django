from django.contrib import admin
from .models import Invitation

@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    ordering = ('-id',)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related()