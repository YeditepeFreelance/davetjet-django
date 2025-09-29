from django.shortcuts import redirect
from django.core.exceptions import ImproperlyConfigured

class RequireActivePackageMixin:
    """
    Redirects to `core:subscribe` if the authenticated user
    does not have a current package.

    Usage:
        class MyView(RequireActivePackageMixin, View):
            ...
    """

    # Optional: allow overriding the redirect URL name
    package_redirect_url = 'core:subscribe'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            # fall back to login_required behaviour if you like
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(request.get_full_path())

        # Make sure profile and get_current_package exist
        if not hasattr(request.user, 'profile'):
            raise ImproperlyConfigured(
                "User model must have a related 'profile' with get_current_package()."
            )

        package = request.user.profile.get_current_package().plan if request.user.profile.get_current_package() else None
        if package is None:
            return redirect(self.package_redirect_url)

        # Store the package for downstream use if handy
        request.current_package = package
        return super().dispatch(request, *args, **kwargs)
