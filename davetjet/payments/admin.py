from django.contrib import admin

from .models import Subscription, Plan, Payment

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'billing_cycle', 'start_date', 'end_date', 'is_active')
    search_fields = ('user__username',)
    list_filter = ('billing_cycle', 'is_active')
    ordering = ('user__username', 'start_date')
    date_hierarchy = 'start_date'
    list_per_page = 20

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'billing_cycle')
    search_fields = ('name',)
    list_filter = ('billing_cycle',)
    ordering = ('name',)
    list_per_page = 20

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('get_user', 'subscription', 'amount', 'currency', 'payment_date', 'status')
    search_fields = ('user__username', 'subscription__plan__name')
    list_filter = ('status', 'currency')
    ordering = ('-payment_date',)
    date_hierarchy = 'payment_date'
    list_per_page = 20

    def has_add_permission(self, request):
        return False    
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False

    def get_user(self, obj):
        return obj.subscription.user if obj.subscription else None
    get_user.short_description = 'User'