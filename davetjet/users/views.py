from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.views import View
from django.views.generic import FormView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from .forms import CustomLoginForm, CustomRegisterForm, UserSettingsForm, ProfileSettingsForm
from .models import User, language_choices, Profile
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.core.exceptions import ValidationError
from django.contrib.auth import logout
from django.contrib.auth.password_validation import validate_password
from django.contrib import messages
import json

@require_GET
def check_username(request):
    username = request.GET.get('username', '').strip()
    is_taken = User.objects.filter(username__iexact=username).exists()
    return JsonResponse({'is_taken': is_taken})

@require_GET
def check_email(request):
    email = request.GET.get('email', '').strip()
    is_taken = User.objects.filter(email__iexact=email).exists()
    return JsonResponse({'is_taken': is_taken})

@require_POST
def check_password(request):
    try:
        data = json.loads(request.body)
        password = data.get('password', '')
        username = data.get('username', '')
        print(username, password)

        # Create a dummy user object with the username for validation
        UserModel = User
        dummy_user = UserModel(username=username)

        # Validate password using Django's validators with user context
        validate_password(password, user=dummy_user)

        return JsonResponse({'valid': True, 'errors': []})
    except ValidationError as e:
        return JsonResponse({'valid': False, 'errors': e.messages})
    except Exception:
        return JsonResponse({'valid': False, 'errors': ['Geçersiz şifre.']})

class DashboardSettingsView(LoginRequiredMixin, View):
    template_name = 'dashboard/settings.html'

    def dispatch(self, request, *args, **kwargs):
        # Create profile if not exists, or get it — must link user
        profile, created = Profile.objects.get_or_create(user=request.user)
        request.user.profile = profile  # Make sure User.profile points to Profile instance
        request.user.save(update_fields=['profile'])  # Save the updated user.profile link
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        user_form = UserSettingsForm(instance=request.user)
        profile_form = ProfileSettingsForm(instance=request.user.profile)
        return render(request, self.template_name, {
            'user_form': user_form,
            'profile_form': profile_form
        })

    def post(self, request):
        user_form = UserSettingsForm(request.POST, instance=request.user)
        profile_form = ProfileSettingsForm(request.POST, request.FILES, instance=request.user.profile)

        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save()
            profile = profile_form.save(commit=False)
            profile.user = user  # explicitly ensure user is set
            profile.save()
            return redirect('core:settings')

        return render(request, self.template_name, {
            'user_form': user_form,
            'profile_form': profile_form,
            'errors': user_form.errors or profile_form.errors
        })

class ForgetPasswordView(View):
    template_name = 'dashboard/forget-password.html'

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name)

    def post(self, request, *args, **kwargs):
        email = request.POST.get('email')
        # Here you would typically handle sending a password reset email
        # For now, we'll just simulate success if the email exists
        if User.objects.filter(email=email).exists():
            # Simulate sending email
            return render(request, self.template_name)
        else:
            return render(request, self.template_name)

class CustomRegisterView(View):
    form_class = CustomRegisterForm
    template_name = 'dashboard/register.html'
    success_url = reverse_lazy('core:create-invitation')
    redirect_authenticated_user = True

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(self.get_success_url())
        form = self.form_class()
        return render(request, self.template_name, {'form': form, 'language_choices': language_choices})

    def post(self, request, *args, **kwargs):
        print('Received POST request for registration')
        form = self.form_class(request.POST, request.FILES)
        if form.is_valid():
            print('Form is valid, saving user...')
            user = form.save()
            login(request, user)
            return redirect(self.get_success_url())
        print('Form is invalid:', form.errors)
        return render(request, self.template_name, {'form': form, 'language_choices': language_choices})

    def get_success_url(self):
        return reverse_lazy('core:dashboard')
class CustomLoginView(LoginView):
    authentication_form = CustomLoginForm
    template_name = 'dashboard/login.html'
    success_url = reverse_lazy('core:dashboard')
    redirect_authenticated_user = True

    def form_valid(self, form):
        login(self.request, form.get_user())
        return redirect(self.get_success_url())

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(self.get_success_url())
        return render(request, self.template_name, {'form': self.get_form()})

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        print(form)
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse_lazy('core:dashboard')

class LogOutView(View):
    def get(self, request, *args, **kwargs):
        logout(request)
        return redirect('core:index')

class DashboardProfileView(LoginRequiredMixin, View):
    template_name = 'dashboard/profile.html'
    login_url = '/login/'

    def get(self, request, *args, **kwargs):
        profile = request.user.profile
        return render(request, 'dashboard/profile.html', {'profile': profile})