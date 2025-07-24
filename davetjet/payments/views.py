from django.shortcuts import render
from django.views import View
from django.views.generic import ListView, DetailView

from .models import Subscription, Plan, Payment

class PaymentTestView(View):
    """
    A simple view to test payment functionality.
    """
    def get(self, request, *args, **kwargs):
        plans = Plan.objects.all()

        return render(request, 'payments/payment.html', {'plans': plans, 'subscription': Subscription.objects.first})

class SubscribeView(View):
    """
    A view to handle subscription creation.
    """
    def get(self, request, *args, **kwargs):
        plans = Plan.objects.all()
        return render(request, 'payments/subscribe.html', {'plans': plans})

    def post(self, request, *args, **kwargs):
        plan_id = request.POST.get('plan_id')
        plan = Plan.objects.filter(id=plan_id).first()

        if not plan: 
            return render(request, 'payments/subscribe.html', {'error': 'Plan not found'}, status=404)

        user = request.user

        if not user.is_authenticated:
            return render(request, 'payments/subscribe.html', {'error': 'You must be logged in to subscribe'}, status=403)

        # Check if the user already has an active subscription for this plan
        existing_subscription = Subscription.objects.filter(user=user, plan=plan.id).first()
        if existing_subscription:
            return render(request, 'payments/subscribe.html', {'error': 'You already have an active subscription for this plan'}, status=400)

        # Create a new subscription
        subscription = Subscription.objects.create(user=user, plan=plan)
        subscription.save()

        # Create a checkout session (placeholder for actual payment gateway integration)
        checkout_session = plan.create_checkout_session(user)

        return render(request, 'payments/subscribe_success.html', {'subscription': subscription, 'checkout_session': checkout_session})

class PaymentView(View):
    """
    A view to handle payment processing.
    """
    def get(self, request, *args, **kwargs):
        return render(request, 'payments/pay.html')

    def post(self, request, *args, **kwargs):
        # Placeholder for actual payment processing logic
        subscription_id = request.POST.get('subscription_id')
        subscription = Subscription.objects.filter(id=subscription_id).first()
        if not subscription:
            return render(request, 'payments/pay.html', {'error': 'Subscription not found'}, status=404)
        
        # Simulate payment processing

        payment = Payment.objects.create(
            subscription=subscription,
            amount=subscription.plan.price,
            currency='USD',
            payment_method='Credit Card',  # Placeholder for actual payment method
            status='completed'  # Simulating a successful payment
        )
        payment.save()

        # Update subscription status

        subscription.is_active = True
        subscription.save()

        # Redirect to success page or render success message
        return render(request, 'payments/payment_success.html', {'message': 'Payment processed successfully'})