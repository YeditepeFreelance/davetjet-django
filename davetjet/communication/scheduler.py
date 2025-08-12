# --- üst kısımda zaten var: imports, URL, send_email vs. ---

from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from typing import Callable
from .network import send_email
import re
import requests
from django.conf import settings

URL = "https://api.netgsm.com.tr/sms/rest/v2/send"

def _normalize_tr_phone(msisdn: str) -> str | None:
    """
    Dönen değer: '5XXXXXXXXX' (10 hane), aksi halde None.
    Kabul edilen örnekler:
      05461234567   -> 5461234567
      5461234567    -> 5461234567
      905461234567  -> 5461234567
      +905461234567 -> 5461234567
    """
    if not msisdn:
        return None
    digits = re.sub(r"\D+", "", msisdn)
    if not digits:
        return None

    # +90 / 90 ile gelmişse, ülke kodunu at
    if digits.startswith("90") and len(digits) >= 12:
        digits = digits[2:]
    # 0 ile gelmişse, baştaki 0'ı at
    if digits.startswith("0") and len(digits) >= 11:
        digits = digits[1:]

    # Artık elimizde 10 haneli olmalı ve 5 ile başlamalı
    if len(digits) == 10 and digits.startswith("5"):
        return digits

    # Bazı edge-case’lerde son 10 haneyi dene
    if len(digits) > 10 and digits[-10:].startswith("5"):
        return digits[-10:]

    return None



class SchedulerService:
    """
    Basit scheduler servisimiz (email için).
    """
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()

    def schedule_email(self, recipients: list, send_time: datetime, callback: Callable = None, *args, **kwargs):
        self.scheduler.add_job(
            send_email,  # senin mevcut fonksiyonun
            'date',
            run_date=send_time,
            kwargs={**kwargs, 'recipients': recipients},
            id=f"email_{hash(tuple(recipients))}_{send_time.timestamp()}"
        )
        if callback:
            self.scheduler.add_job(
                callback,
                'date',
                run_date=send_time,
                args=args,
                kwargs=kwargs
            )

    def shutdown(self):
        self.scheduler.shutdown()


class EnhancedSchedulerService(SchedulerService):
    """
    Netgsm batch SMS entegrasyonu ile geliştirilmiş scheduler.
    """
    def __init__(self, sms_username: str, sms_password: str, msgheader: str | None = None):
        super().__init__()
        self.sms_username = sms_username
        self.sms_password = sms_password
        # Netgsm'de başlık (onaylı originator). Boş bırakılırsa username'i kullanır.
        self.msgheader = msgheader or sms_username

    # ---- PUBLIC API ----
    def schedule_sms(self, recipients: list[str], send_time: datetime, message: str, header: str | None = None):
        """
        recipients: ['0546...', '90532...', '+90532...'] gibi karışık gelebilir; normalize ediyoruz.
        send_time: datetime
        message: str
        header: override etmek istersen
        """
        clean_numbers = []
        for r in recipients or []:
            n = _normalize_tr_phone(r)
            if n:
                clean_numbers.append(n)

        if not clean_numbers:
            # hiç geçerli numara yoksa job eklemeye gerek yok
            return

        self.scheduler.add_job(
            self._send_sms_batch_job,
            'date',
            run_date=send_time,
            kwargs={
                "numbers": clean_numbers,
                "message": message,
                "header": header or self.msgheader,
            },
            id=f"sms_{hash(tuple(clean_numbers))}_{send_time.timestamp()}"
        )

    def send_sms_now(self, recipients: list[str], message: str, header: str | None = None) -> dict | None:
        """
        İstersen anında (schedule etmeden) SMS gönderimi.
        """
        clean_numbers = []
        for r in recipients or []:
            n = _normalize_tr_phone(r)
            if n:
                clean_numbers.append(n)
        if not clean_numbers:
            return None
        return self._send_sms_batch(numbers=clean_numbers, message=message, header=header or self.msgheader)

    # ---- INTERNAL ----
    def _send_sms_batch_job(self, numbers: list[str], message: str, header: str):
        """
        APScheduler job entrypoint: batch SMS gönder.
        """
        resp = self._send_sms_batch(numbers=numbers, message=message, header=header)
        # burada istersen logging veya DB'ye jobid yaz
        return resp

    def _send_sms_batch(self, numbers: list[str], message: str, header: str) -> dict | None:
        """
        Netgsm REST v2 /send endpoint'ine toplu istek atar.
        """
        payload = {
            "msgheader": settings.NETGSM_USERNAME,
            "messages": [{"msg": message, "no": n} for n in numbers],
            "encoding": "TR",
            "iysfilter": "",
            "partnercode": "",
        }

        try:
            r = requests.post(
                URL,
                json=payload,
                auth=(self.sms_username, self.sms_password),  # Basic Auth
                timeout=20
            )
            r.raise_for_status()
        except requests.RequestException as e:
            print("NETGSM ERR:", e)
            return None

        try:
            resp = r.json()
        except ValueError:
            print("NETGSM RESP (non-json):", r.text)
            return None

        # beklenen alanlar: code, jobid, description
        code = resp.get("code")
        if code == "00":
            # başarı
            return resp
        # hata
        print("NETGSM ERROR RESP:", resp)
        return resp
