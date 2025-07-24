from django.db import models

from users.models import User

from davetjet.config import billing_cycles


class Subscription(models.Model):
    """
    Model to manage user subscriptions.
    """
    
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='subscription_set')
    plan = models.ForeignKey('Plan', on_delete=models.CASCADE, related_name='subscriptions', blank=True, null=True)
    plan_name = models.CharField(max_length=100, blank=True, null=True) 
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(default=False)

    # Trial period management

    trial_start_date = models.DateTimeField(blank=True, null=True)
    trial_end_date = models.DateTimeField(blank=True, null=True)

    # Payment information

    payment_method = models.CharField(max_length=50, blank=True, null=True)
    
    # Billing cycle

    billing_cycle = models.CharField(max_length=20, choices=billing_cycles or list, default='monthly') 
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    currency = models.CharField(max_length=10, default='USD')

    next_payment_date = models.DateTimeField(blank=True, null=True)
    last_payment_date = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} - {self.plan_name}"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.plan_name = self.plan.name if self.plan else 'No Plan'

    class Meta:
        verbose_name = 'Subscription'
        verbose_name_plural = 'Subscriptions'
        ordering = ['user__username', 'start_date']

class Plan(models.Model):
    """
    Model to define subscription plans.
    """

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    billing_cycle = models.CharField(max_length=20, choices=billing_cycles or list, default='monthly')
    features = models.JSONField(default=dict, blank=True)

    subscribers = models.ManyToManyField(User, related_name='plans', blank=True)

    def create_checkout_session(self, user):
        """
        Create a checkout session for the plan.
        This method should integrate with a payment gateway to create a session.
        """
        # Placeholder for actual payment gateway integration
        return f"Checkout session created for {user.username} with plan {self.name}"

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Plan'
        verbose_name_plural = 'Plans'
        ordering = ['name']

class Payment(models.Model):
    """
    Model to manage payments for subscriptions.
    """
    
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default='USD')
    payment_date = models.DateTimeField(auto_now_add=True)
    payment_method = models.CharField(max_length=50, blank=True, null=True)
    status = models.CharField(max_length=20, default='pending')
    invoice_number = models.CharField(max_length=50, unique=True, blank=True, null=True)

    def __str__(self):
        return f"Payment for {self.subscription.user.username} - {self.amount} {self.currency}"

    class Meta:
        verbose_name = 'Payment'
        verbose_name_plural = 'Payments'
        ordering = ['payment_date']

