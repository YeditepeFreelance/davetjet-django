from apscheduler.schedulers.background import BackgroundScheduler, BlockingScheduler
from .network import send_email, send_email_via_resend
from datetime import datetime
from typing import Callable
import sys

class SchedulerService:
  """
  A service for scheduling communication tasks such as sending emails, SMS, and WhatsApp messages.
  This service uses APScheduler to manage scheduled tasks in the background.
  """
  def __init__(self):
    self.scheduler = BackgroundScheduler()
    self.scheduler.start()

  def schedule_email(self, recipients: list, send_time: datetime, callback: Callable, *args, **kwargs):
    print(f"Scheduling email to {recipients} at {send_time}", file=sys.stderr)
    self.scheduler.add_job(
      send_email,
      'date',
      run_date=send_time,
      kwargs={**kwargs, 'recipients': recipients},
      id=f"email_{recipients}_{send_time.timestamp()}"
    )
    self.scheduler.add_job(
      callback,
      'date',
      run_date=send_time,
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