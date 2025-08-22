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

# invitations/utils.py
from bs4 import BeautifulSoup
from django.conf import settings
import os, json

def _ensure_el(soup: BeautifulSoup, css_sel: str, tag: str = "span"):
    """
    CSS seçici olarak #id bekler; yoksa body sonuna ilgili id’yle tag yaratır.
    """
    el = soup.select_one(css_sel)
    if el:
        return el
    if css_sel.startswith("#"):
        new_el = soup.new_tag(tag, id=css_sel[1:])
    else:
        new_el = soup.new_tag(tag)
    (soup.body or soup).append(new_el)
    return new_el
import os, json, copy
from bs4 import BeautifulSoup
from django.conf import settings
import copy

def _force_css_from_file(soup, file_soup):
    """
    soup içindeki TÜM CSS'i (style + <link rel=stylesheet>) temizler
    ve file_soup'tan gelenlerle kesin olarak değiştirir.
    <head> yoksa oluşturur; o da yoksa fragmanda en üste enjekte eder.
    """
    # 1) Mevcut style/link'leri kaldır
    for tag in list(soup.find_all("style")):
        tag.decompose()
    for link in list(soup.find_all("link")):
        rel = link.get("rel") or []
        if any(r.lower() == "stylesheet" for r in rel):
            link.decompose()

    # 2) Dosyadan CSS'leri topla
    file_links = []
    for link in file_soup.find_all("link"):
        rel = link.get("rel") or []
        if any(r.lower() == "stylesheet" for r in rel):
            file_links.append(copy.deepcopy(link))

    file_styles = [copy.deepcopy(s) for s in file_soup.find_all("style")]

    # 3) <head> hedefini hazırla (yoksa yarat)
    head = soup.head
    if head is None:
        if soup.html:  # <html> var ama head yok
            head = soup.new_tag("head")
            soup.html.insert(0, head)
        elif soup.body:  # <body> var ama html yok (fragman)
            # html > head > body sarımı oluştur
            html = soup.new_tag("html")
            head = soup.new_tag("head")
            html.append(head)
            body = soup.body
            html.append(body.extract())
            soup.append(html)
        else:
            # Tam fragman: head yaratamayız, doğrudan dokümanın başına enjekte ederiz (fallback)
            # Bu durumda link/style'ları BODY’de tutmak sorun olmaz; tarayıcı yine uygular.
            for node in reversed(file_links + file_styles):
                soup.insert(0, node)
            return

    # 4) Normal yol: önce link’ler, sonra style’lar (doğal yükleme sırası)
    for l in file_links:
        head.append(l)
    for s in file_styles:
        head.append(s)

def build_invitation_html(
    invitation,
    *,
    request=None,
    show_rsvp: bool = True,
    embed_recipients: bool = True,
    keep_contenteditable: bool = False,
) -> str:
    """
    - Şablon kaynağı: varsa invitation.template_html, yoksa dosya.
    - AMA: RSVP bölümü, TÜM <script>’ler ve TÜM CSS (<style> + <link rel="stylesheet">) her zaman dosyadan yenilenir.
    - #event-* alanları doldurulur, slug/link yazılır.
    - show_rsvp=True ise .rsvp üstündeki 'hide-in-embed' kaldırılır; False ise eklenir.
    - Dosyada RSVP yoksa minimal bir form eklenir (autocomplete yapısına uyumlu input-wrap + suggestions).
    - keep_contenteditable=False ise contenteditable atributları kaldırılır.
    - embed_recipients=True ise alıcılar JSON olarak gömülür + küçük helper eklenir.
    """

    # --- Dosya yolunu hazırla (RSVP, SCRIPT, CSS mutlaka buradan gelecek)
    template_path = os.path.join(
        settings.BASE_DIR, "static", "inv-temps", f"{invitation.template}.html"
    )
    if not os.path.exists(template_path):
        return "<h1>Şablon bulunamadı</h1>"

    with open(template_path, encoding="utf-8") as f:
        file_soup = BeautifulSoup(f.read(), "html.parser")

    # --- Başlangıç soup'u: DB'den mi, dosyadan mı?
    markup = (getattr(invitation, "template_html", "") or "").strip()
    if markup:
        soup = BeautifulSoup(markup, "html.parser")
    else:
        soup = BeautifulSoup(str(file_soup), "html.parser")

    # ------- Yardımcılar -------
    def _ensure_el(soup_obj, css_sel, tag_name="span"):
        el = soup_obj.select_one(css_sel)
        if el: return el
        if css_sel.startswith("#"):
            new_el = soup_obj.new_tag(tag_name, id=css_sel[1:])
        else:
            new_el = soup_obj.new_tag(tag_name)
        (soup_obj.body or soup_obj).append(new_el)
        return new_el

    def _set_text(el, val):
        if el is None: return
        el.clear()
        el.append(val if val is not None else "")

    def _set_attr(el, name, val):
        if el is None: return
        if val is None:
            el.attrs.pop(name, None)
        else:
            el.attrs[name] = val

    def _ensure_head(soup_obj):
        if soup_obj.head:
            return soup_obj.head
        # head yoksa oluştur
        if not soup_obj.html:
            html_tag = soup_obj.new_tag("html")
            body = soup_obj.body or soup_obj.new_tag("body")
            html_tag.append(soup_obj.new_tag("head"))
            html_tag.append(body)
            soup_obj.append(html_tag)
        elif not soup_obj.head:
            soup_obj.html.insert(0, soup_obj.new_tag("head"))
        return soup_obj.head

    def _insert_after_anchor_or_append(nodes):
        anchor = soup.select_one(".divider-soft")
        if nodes:
            if anchor and hasattr(anchor, "insert_after"):
                last = anchor
                for n in nodes:
                    last = last.insert_after(copy.deepcopy(n))
            else:
                container = soup.body or soup
                for n in nodes:
                    container.append(copy.deepcopy(n))

    # ------- 1) RSVP'leri ve scriptleri DB içinden kaldır, dosyadan yeniden ekle -------
    # RSVP’leri temizle
    for old_rsvp in soup.select("section.rsvp"):
        old_rsvp.decompose()
    # TÜM scriptleri temizle (data-json vs. hepsi; en sonda kendi helper'ımızı ekleyeceğiz)
    for old_script in soup.find_all("script"):
        old_script.decompose()

    # Dosyadan RSVP al
    file_rsvps = file_soup.select("section.rsvp")
    if file_rsvps:
        _insert_after_anchor_or_append(file_rsvps)
    else:
        # Dosyada RSVP yoksa minimal form ekle (autocomplete uyumlu)
        rsvp = soup.new_tag("section", **{
            "class": "rsvp" + ("" if show_rsvp else " hide-in-embed"),
            "aria-labelledby": "rsvpTitle",
            "id": "rsvpRoot",
        })
        h2 = soup.new_tag("h2", id="rsvpTitle"); h2.string = "Katılım Bildirimi"; rsvp.append(h2)
        row = soup.new_tag("div", **{"class":"row", "style":"margin-bottom:10px"})
        wrap = soup.new_tag("div", **{"class":"input-wrap"})
        inp = soup.new_tag("input", id="rsvp-name", **{
            "class":"input", "type":"text", "placeholder":"Adınız",
            "autocomplete":"off", "aria-autocomplete":"list",
            "aria-expanded":"false", "aria-controls":"name-suggestions"
        })
        sugg = soup.new_tag("div", id="name-suggestions", **{
            "class":"suggestions", "role":"listbox", "aria-live":"polite"
        })
        wrap.append(inp); wrap.append(sugg); row.append(wrap); rsvp.append(row)
        chips = soup.new_tag("div", **{"class":"chips", "role":"group", "aria-label":"Katılım durumu"})
        for label, val in [("Geleceğim","yes"), ("Emin Değilim","maybe"), ("Gelmeyeceğim","no")]:
            chip = soup.new_tag("div", **{"class":"chip", "tabindex":"0"})
            chip["data-status"] = val; chip.string = label; chips.append(chip)
        rsvp.append(chips)
        btn = soup.new_tag("button", id="rsvp-submit", **{"class":"btn", "disabled": True}); btn.string = "Gönder"; rsvp.append(btn)
        msg = soup.new_tag("div", id="rsvp-msg", **{"class":"msg"}); rsvp.append(msg)
        anchor = soup.select_one(".divider-soft")
        if anchor and hasattr(anchor, "insert_after"):
            anchor.insert_after(rsvp)
        else:
            (soup.body or soup).append(rsvp)

    # Dosyadan SCRIPT’leri ekle (inline + src)
    file_scripts = file_soup.find_all("script")
    for s in file_scripts:
        (soup.body or soup).append(copy.deepcopy(s))

    # ------- 2) CSS’i de her zaman dosyadan yenile -------
    # Mevcut <style> ve <link rel="stylesheet"> etiketlerini kaldır
    for tag in soup.find_all("style"):
        tag.decompose()
    for link in soup.find_all("link"):
        rel = link.get("rel") or []
        if any(r.lower() == "stylesheet" for r in rel):
            link.decompose()

    # Dosyadaki CSS etiketlerini al ve HEAD’e koy
    head = _ensure_head(soup)
    # önce link'ler, sonra style'lar (tipik yükleme sırası)
    for link in file_soup.find_all("link"):
        rel = link.get("rel") or []
        if any(r.lower() == "stylesheet" for r in rel):
            head.append(copy.deepcopy(link))
    for style in file_soup.find_all("style"):
        head.append(copy.deepcopy(style))

    # ------- 3) Metin yerleştirmeleri -------
    dt = getattr(invitation, "invitation_date", None)
    date_str = dt.strftime("%d.%m.%Y") if dt else ""
    time_str = dt.strftime("%H:%M") if dt else ""

    mapping = {
        "#event-title":    invitation.name,
        "#event-date":     date_str,   # dd.mm.yyyy
        "#event-time":     time_str,   # HH:MM
        "#event-message":  getattr(invitation, "message", "") or "",
        "#event-location": getattr(invitation, "location", "") or "",
    }
    for css_sel, val in mapping.items():
        el = soup.select_one(css_sel) or _ensure_el(soup, css_sel, "span")
        _set_text(el, val)

    # ------- 4) Slug ve linkler -------
    _set_text(soup.select_one("#inv-slug"), invitation.slug)
    _set_attr(soup.select_one("#rsvp-link"), "href", f"/invitations/{invitation.slug}/")
    _set_attr(soup.select_one("#inv-slug-input"), "value", invitation.slug)

    # ------- 5) contenteditable kapat (public/PDF) -------
    if not keep_contenteditable:
        for tag in soup.find_all(attrs={"contenteditable": True}):
            tag.attrs.pop("contenteditable", None)

    # ------- 6) RSVP görünürlüğü (dosyadan gelenlere uygula) -------
    for rsvp in soup.select("section.rsvp"):
        classes = rsvp.get("class", [])
        if show_rsvp:
            rsvp["class"] = [c for c in classes if c != "hide-in-embed"]
        else:
            if "hide-in-embed" not in classes:
                classes.append("hide-in-embed")
            rsvp["class"] = classes

    # ------- 7) Alıcı JSON + helper (dosyadan gelen scriptlerin ARDINDAN eklenir) -------
    if embed_recipients:
        try:
            recs = invitation.recipients.all().only("id", "name")
            data_tag = soup.new_tag("script", type="application/json", id="inv-recipients")
            data_tag.string = json.dumps(
                [{"id": r.id, "name": r.name} for r in recs],
                ensure_ascii=False
            )
            (soup.body or soup).append(data_tag)

            helper_js = soup.new_tag("script")
            helper_js.string = """
            (function(){
              try {
                const raw = document.getElementById('inv-recipients')?.textContent || '[]';
                window.RECIPIENTS = JSON.parse(raw);
              } catch(e){ window.RECIPIENTS = []; }
            })();
            """
            (soup.body or soup).append(helper_js)
        except Exception:
            pass
    _force_css_from_file(soup, file_soup)

    return str(soup)
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
