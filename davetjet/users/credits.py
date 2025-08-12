# reminders/credits.py
from django.core.exceptions import ValidationError
from django.db import transaction

def _pick_wallet(user):
    """
    Kullanıcının hatırlatma kredisi tuttuğu alanı bul:
    - user.reminder_credits  veya
    - user.profile.reminder_credits
    Yoksa None döner.
    """
    if hasattr(user, "reminder_credits"):
        return user, "reminder_credits"
    profile = getattr(user, "profile", None)
    if profile and hasattr(profile, "reminder_credits"):
        return profile, "reminder_credits"
    return None, None

def get_reminder_credits(user) -> int:
    holder, attr = _pick_wallet(user)
    return getattr(holder, attr, 0) if holder else 0

@transaction.atomic
def consume_reminder_credits(user, count: int):
    if count <= 0:
        return
    holder, attr = _pick_wallet(user)
    if not holder:
        raise ValidationError("Hatırlatma haklarınız tanımlı değil.")
    current = getattr(holder, attr, 0)
    if current < count:
        raise ValidationError("Yetersiz hatırlatma hakkı.")
    setattr(holder, attr, current - count)
    holder.save(update_fields=[attr])
