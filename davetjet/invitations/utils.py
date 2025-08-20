# invitations/utils/secure_links.py
import json
from urllib.parse import quote
from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings

fernet = Fernet(settings.FERNET_KEY)

def _site_base(base_url=None):
    return base_url or getattr(settings, "SITE_URL", "https://davetjet-webapp.onrender.com")

def _token_payload(invitation):
    return {"id": invitation.id, "p": (invitation.password or "")}

def generate_secure_invitation_link(invitation, base_url=None):
    """
    Eski sürüm (query param). Dilersen kullanmaya devam edebilirsin.
    """
    token = fernet.encrypt(json.dumps(_token_payload(invitation)).encode()).decode()
    base = _site_base(base_url)
    return f"{base}/invitations/{invitation.slug}/"
    return f"{base}/invitations/{invitation.slug}/?access={quote(token)}"

def generate_entry_url(invitation, base_url=None):
    """
    ÖNERİLEN: Cookie ayarlayıp temiz URL’ye yönlendiren giriş linki.
    /i/<slug>/a/<token>/ -> (cookie set) -> 302 -> /invitations/<slug>/
    """
    token = fernet.encrypt(json.dumps(_token_payload(invitation)).encode()).decode()
    base = _site_base(base_url)
    return f"{base}/i/{invitation.slug}/a/{quote(token)}/"

def match_invitation(invitation, access_token: str, ttl_seconds: int | None = None) -> bool:
    try:
        # ttl_seconds verirsen link/cookie süreli olur.
        raw = fernet.decrypt(access_token.encode(), ttl=ttl_seconds) if ttl_seconds \
              else fernet.decrypt(access_token.encode())
        data = json.loads(raw.decode())
    except InvalidToken:
        return False
    except Exception:
        return False
    if str(data.get("id")) != str(invitation.id):
        return False
    if (invitation.password or "") != (data.get("p") or ""):
        return False
    return True


# invitations/utils/secure_links.py (aynı dosyada)
def get_token_from_request(request, invitation):
    """
    Önce cookie, sonra query paramdan token çek.
    """
    cookie_name = f"inv_access_{invitation.id}"
    token = request.COOKIES.get(cookie_name)
    if not token:
        token = request.GET.get("access")
    return token

def has_access(request, invitation, ttl_seconds: int | None = None) -> bool:
    token = get_token_from_request(request, invitation)
    return bool(token and match_invitation(invitation, token, ttl_seconds=ttl_seconds))


import os
from bs4 import BeautifulSoup, NavigableString
from django.conf import settings


def _set_text(el, text):
    """Element içeriğini güvenle metinle değiştir."""
    el.clear()
    el.append(NavigableString(text if text is not None else ""))

def _set_attr(el, attr, val):
    el[attr] = val if val is not None else ""

def render_invitation_html(invitation):
    template_filename = f"{invitation.template}.html"
    template_path = os.path.join(settings.BASE_DIR, "static", "inv-temps", template_filename)

    with open(template_path, encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    # Tarih/saat parçala
    dt = invitation.invitation_date
    date_str = dt.strftime("%d.%m.%Y") if dt else ""
    time_str = dt.strftime("%H:%M") if dt else ""

    # Metin alanlarını yaz
    replacements = {
        "event-title": invitation.name,
        "event-date": date_str,
        "event-time": time_str,
        "event-message": invitation.message or "",
        "event-location": getattr(invitation, "location", "") or "",
    }
    for el_id, val in replacements.items():
        el = soup.find(id=el_id)
        if el:
            _set_text(el, val)

    # SLUG: metin olarak basmak (ör: <span id="inv-slug"></span>)
    inv_slug_el = soup.find(id="inv-slug")
    if inv_slug_el:
        _set_text(inv_slug_el, invitation.slug)

    # SLUG: link attribute olarak basmak (ör: <a id="rsvp-link"></a>)
    rsvp_link = soup.find(id="rsvp-link")
    if rsvp_link:
        _set_attr(rsvp_link, "href", f"/i/{invitation.slug}")

    # Örn: gizli input’a koymak (ör: <input id="inv-slug-input">)
    slug_input = soup.find(id="inv-slug-input")
    if slug_input:
        _set_attr(slug_input, "value", invitation.slug)

    # Edit’i e-posta için kapatmak istersen:
    for tag in soup.find_all(attrs={"contenteditable": True}):
        del tag["contenteditable"]

    return str(soup)
