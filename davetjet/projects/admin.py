from django.contrib import admin
from .models import Project

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'start_date', 'end_date', 'is_active', 'is_archived')
    search_fields = ('name', 'owner__username')
    list_filter = ('is_active', 'is_archived', 'start_date', 'end_date')
    ordering = ('-created_at',)
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('owner')