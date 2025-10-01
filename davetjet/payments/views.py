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

import hmac, hashlib, base64
from django.http import HttpResponse
from django.utils.encoding import force_bytes

def paytr_callback(request):
    if request.method != 'POST':
        return HttpResponse(status=405)

    merchant_oid  = request.POST.get('merchant_oid', '')
    status        = request.POST.get('status', '')
    total_amount  = request.POST.get('total_amount', '')
    hash_received = request.POST.get('hash', '')

    # Keys ve salt bytes olarak normalize ediliyor
    merchant_key  = settings.MERCHANT_KEY if isinstance(settings.MERCHANT_KEY, bytes) else settings.MERCHANT_KEY.encode("utf-8")
    merchant_salt = settings.MERCHANT_SALT if isinstance(settings.MERCHANT_SALT, bytes) else settings.MERCHANT_SALT.encode("utf-8")

    # Doğru hash string sırası: merchant_oid + merchant_salt + status + total_amount
    hash_str = merchant_oid.encode("utf-8") + merchant_salt + status.encode("utf-8") + total_amount.encode("utf-8")

    # HMAC hesaplama (binary digest → base64)
    hmac_digest = hmac.new(merchant_key, hash_str, hashlib.sha256).digest()
    hash_calculated = base64.b64encode(hmac_digest).decode("utf-8")

    if hash_received != hash_calculated:
        return HttpResponse('Invalid hash', status=400)

    # Payment kaydını bul
    try:
        payment = Payment.objects.get(merchant_oid=merchant_oid)
    except Payment.DoesNotExist:
        return HttpResponse('Payment not found', status=404)

    # Tekrar işleme engeli
    if not payment.processed:
        payment.status = status
        payment.total_amount = total_amount
        payment.processed = True
        payment.save()

        # Başarılı ödeme ise paketi kullanıcıya ata
        if status == "success" and payment.user:
            package = payment.package
            payment.user.profile.add_new_package(package)

    # PayTR her zaman 'OK' bekler
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