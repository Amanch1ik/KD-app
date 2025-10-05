from celery import shared_task
from django.utils import timezone


@shared_task
def sample_heartbeat():
    # Simple heartbeat task for monitoring/cron via celery beat
    return f"heartbeat {timezone.now().isoformat()}"


