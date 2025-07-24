from django.contrib import admin
from django.contrib.auth.models import Group

from .models import User, Profile

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'is_verified', 'is_active', 'last_login')
    search_fields = ('username', 'email')
    list_filter = ('is_verified', 'is_active')
    ordering = ('username',)

    def has_add_permission(self, request):
        return False

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'full_name', 'company_name', 'language')
    search_fields = ('user__username', 'full_name', 'company_name')
    list_filter = ('language',)
    ordering = ('user__username',)

    def has_add_permission(self, request):
        return False

admin.site.unregister(Group) 