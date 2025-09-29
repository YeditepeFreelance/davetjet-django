# core/decorators.py
from functools import wraps
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages

# get_page_permissions çıktını URL name'lerine eşleştir
PERMISSION_ROUTE_MAP = {
    "create-invitation": "core:create-invitation",
    "edit-recipients-list": "core:recipients",  # gerekirse değiştir
    # "another-key": "app:viewname",
}

def _current_view_name(request):
    rm = getattr(request, "resolver_match", None)
    if not rm:
        return "", ""
    name = rm.url_name or ""
    ns = rm.namespace or ""
    return name, f"{ns}:{name}" if ns else name

def require_full_access(view_func=None, *, allow=None, message=True):
    """
    Kullanıcı `get_page_permissions` != 'all' ise uygun sayfaya yönlendirir.
    - allow: ['core:create_invitation', 'recipients'] gibi whitelist (url_name ya da ns:name)
    - message=True: redirect öncesi küçük bir info mesajı basar
    """
    allow = set(allow or [])

    def decorator(func):
        @wraps(func)
        def _wrapped(request, *args, **kwargs):
            user = getattr(request, "user", None)
            # Anonim ise: login'e gönder (isteğe göre değiştir)
            if not getattr(user, "is_authenticated", False):
                login_url = reverse("core:login")
                return redirect(f"{login_url}?next={request.get_full_path()}")

            # staff/superuser serbest bırakalım
            if getattr(user, "is_staff", False) or getattr(user, "is_superuser", False):
                return func(request, *args, **kwargs)

            # property olduğu için doğrudan string bekliyoruz
            perm_key = getattr(user, "get_page_permissions", "all")

            # Tam yetki -> geç
            if perm_key == "all":
                return func(request, *args, **kwargs)

            # Hedef view (örn. 'core:create_invitation')
            target_viewname = PERMISSION_ROUTE_MAP.get(perm_key)
            if not target_viewname:
                # Eşleşme yoksa güvenli tarafta kal: view'ı çalıştır
                return func(request, *args, **kwargs)

            # Şu anki view, hedefin kendisiyse veya allow listesindeyse: geç
            cur_name, cur_ns_name = _current_view_name(request)
            if cur_name in allow or cur_ns_name in allow:
                return func(request, *args, **kwargs)
            if cur_ns_name == target_viewname or cur_name == target_viewname.split(":")[-1]:
                return func(request, *args, **kwargs)

            target_url = reverse(target_viewname)

            # AJAX/JSON ise JSON ile yönlendirme bilgisi
            accepts = request.headers.get("Accept", "")
            is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
            if is_ajax or "application/json" in accepts:
                # 428: client’tan aksiyon bekleniyor -> frontend redirect edebilir
                return JsonResponse({"redirect": target_url, "reason": perm_key}, status=428)

            if message:
                pass
                # messages.info(request, "Devam etmeden önce gerekli adımları tamamlayın.")

            return redirect(target_url)

        return _wrapped
    return decorator(view_func) if view_func else decorator
