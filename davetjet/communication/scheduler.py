from apscheduler.schedulers.background import BackgroundScheduler, BlockingScheduler
from .network import send_email, send_email_via_resend
from datetime import datetime
from typing import Callable
import sys

from netgsm import Netgsm
from django.conf import settings

# Initialize the SDK
netgsm = Netgsm(
    username=settings.NETGSM_USERNAME,   # Your Netgsm username
    password=settings.NETGSM_PASSWORD,   # Your Netgsm password
)

# response = netgsm.sms.send(
#     msgheader="HEADER",
#     messages=[
#         {
#             "msg": "Hello world!",
#             "no": "5XXXXXXXXX"
#         }
#     ]
# )

# print(response)


class SchedulerService:
  """
  A service for scheduling communication tasks such as sending emails, SMS, and WhatsApp messages.
  This service uses APScheduler to manage scheduled tasks in the background.
  """
  def __init__(self):
    self.scheduler = BackgroundScheduler()
    self.scheduler.start()

  def schedule_email(self, recipients: list, send_time: datetime, callback: Callable = None, *args, **kwargs):
    print(f"Scheduling email to {recipients} at {send_time}", file=sys.stderr)
    self.scheduler.add_job(
      send_email,
      'date',
      run_date=send_time,
      kwargs={**kwargs, 'recipients': recipients},
      id=f"email_{recipients}_{send_time.timestamp()}"
    )
    if callback:
      self.scheduler.add_job(
        callback,
        'date',
        run_date=send_time,
        args=args,
        kwargs=kwargs
      )

  def schedule_sms(self, send_func: Callable, recipient: str, send_time: datetime, *args, **kwargs):
    self.scheduler.add_job(
      send_func,
      'date',
      run_date=send_time,
      args=(recipient, *args),
      kwargs=kwargs,
      id=f"sms_{recipient}_{send_time.timestamp()}"
    )

  def schedule_whatsapp(self, send_func: Callable, recipient: str, send_time: datetime, *args, **kwargs):
    self.scheduler.add_job(
      send_func,
      'date',
      run_date=send_time,
      args=(recipient, *args),
      kwargs=kwargs,
      id=f"whatsapp_{recipient}_{send_time.timestamp()}"
    )

  def shutdown(self):
    self.scheduler.shutdown()

class EnhancedSchedulerService(SchedulerService):
    def __init__(self, sms_username, sms_password, msgheader=None):
        super().__init__()
        self.sms_username = sms_username
        self.sms_password = sms_password
        self.msgheader = msgheader or sms_username

    def schedule_sms(self, recipients, send_time, message):
        """
        Recipients: list of phone numbers (strings).
        send_time: datetime object
        message: str
        """
        # Zamanlama kısmı scheduler'ın altyapısına bağlı
        self.schedule(
            recipients=recipients,
            send_time=send_time,
            subject="[SMS Reminder]",  # placeholder
            message=message,
            method="sms",
            callback=lambda success: self._sms_callback(success, recipients)
        )
    def _sms_callback(self, success, recipients):
        # Callback sonrası loglama veya veritabanı güncelleme
        status = "başarılı" if success else "başarısız"
        print(f"SMS gönderimi {status} : {recipients}")

