from datetime import datetime, timezone
from types import SimpleNamespace
from worker import fetch_price

from apscheduler.schedulers.base import STATE_RUNNING
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.job import Job

# Suppress timezone warnings
import warnings

# Ignore dateparser warnings regarding pytz
warnings.filterwarnings(
    "ignore",
    message="The localize method is no longer necessary, as this time zone supports the fold attribute",
)

scheduler = BackgroundScheduler()


def init_jobs(config: SimpleNamespace):
    global scheduler
    
    if scheduler.state == STATE_RUNNING:
        scheduler.shutdown(wait=True)
        
    scheduler.remove_all_jobs()

    scheduler = BackgroundScheduler()

    for i, r in enumerate(config.rules):
        # Set cron
        t = CronTrigger.from_crontab(f'0 {r.hours} * * *')
        t.jitter = 600

        # Schedule
        scheduler.add_job(fetch_price, t, name=r.name, kwargs={'rule': r, 'config': config, 'idx': i})

    scheduler.start()

def get_jobs() -> list[dict]:
    jobs: list[Job] = scheduler.get_jobs()

    return ({
        'name': j.name,
        'next': j.next_run_time,
        'delta': (j.next_run_time.replace(tzinfo=timezone.utc) - datetime.now().replace(tzinfo=timezone.utc))
    } for j in jobs)

def run_now():
    jobs: list[Job] = scheduler.get_jobs()

    for j in jobs:
        j.modify(next_run_time=datetime.now())
