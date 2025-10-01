import sys
import uuid
from django.shortcuts import render
from django.views import View
from django.views.generic import ListView, DetailView

from .models import Subscription, Plan, Payment

from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.utils.encoding import force_bytes
import hashlib, hmac, base64
from django.conf import settings
from .models import Payment

@csrf_exempt
def paytr_notify(request):
    if request.method != 'POST':
        return HttpResponse(status=405)

    merchant_oid  = request.POST.get('merchant_oid', '')
    status        = request.POST.get('status', '')
    total_amount  = request.POST.get('total_amount', '')
    hash_received = request.POST.get('hash', '')

    # Hash doğrulama
    merchant_key  = force_bytes(settings.MERCHANT_KEY)
    merchant_salt = settings.MERCHANT_SALT
    hash_str = f"{merchant_oid}{status}{total_amount}{merchant_salt}"
    hash_calculated = base64.b64encode(
        hmac.new(merchant_key, force_bytes(hash_str), hashlib.sha256).digest()
    ).decode()

    print(hash_received, hash_calculated, file=sys.stderr)  # Debug için
    print(hash_received == hash_calculated, file=sys.stderr)  # Debug için
    if hash_received != hash_calculated:
        return HttpResponse('Invalid hash', status=400)

    # Payment kaydını bul
    try:
        payment = Payment.objects.get(merchant_oid=merchant_oid)
    except Payment.DoesNotExist:
        return HttpResponse('Payment not found', status=404)

    # Daha önce işlenmişse tekrar işleme
    if not payment.processed:
        payment.status = status
        payment.total_amount = total_amount
        payment.processed = True
        payment.save()

        # Ödeme başarılıysa plan atama
        if status == "success" and payment.user:
            package = payment.package  # FK Package sayesinde direkt alıyoruz
            payment.user.profile.add_new_package(package)

    # Her zaman OK dön
    return HttpResponse('OK')

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