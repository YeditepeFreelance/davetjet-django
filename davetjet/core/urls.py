from django.shortcuts import render
from django.urls import path

app_name = 'core'

urlpatterns = [
    path('', lambda request: render(request, 'landing/index.html'), name='index'),
]