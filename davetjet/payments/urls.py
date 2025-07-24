from django.urls import path

from .views import PaymentTestView, SubscribeView, PaymentView

app_name = 'payments'

urlpatterns = [
  path('test', PaymentTestView.as_view(), name='payment_test'),

  path('subscribe', SubscribeView.as_view(), name='subscribe'),
  path('pay', PaymentView.as_view(), name='pay'),
]