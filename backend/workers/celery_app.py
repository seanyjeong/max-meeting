"""
Celery application configuration.

Configures Celery with Redis broker and result backend.
Uses task_acks_late=True for reliability (spec Section 6).
"""

from celery import Celery
from kombu import Exchange, Queue

from app.config import get_settings

settings = get_settings()

# Create Celery app
celery_app = Celery(
    "max_meeting_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

# Configure Celery
celery_app.conf.update(
    # Task acknowledgment
    task_acks_late=settings.CELERY_TASK_ACKS_LATE,
    task_reject_on_worker_lost=True,

    # Time limits
    task_time_limit=settings.CELERY_TASK_TIME_LIMIT,
    task_soft_time_limit=settings.CELERY_TASK_SOFT_TIME_LIMIT,

    # Worker concurrency
    worker_concurrency=settings.CELERY_WORKER_CONCURRENCY,
    worker_prefetch_multiplier=1,  # Fetch one task at a time for heavy tasks

    # Serialization
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],

    # Timezone
    timezone="Asia/Seoul",
    enable_utc=True,

    # Result backend settings
    result_expires=86400,  # 24 hours
    result_extended=True,

    # Task tracking
    task_track_started=True,
    task_send_sent_event=True,

    # Error handling
    task_default_retry_delay=60,  # 1 minute default retry delay

    # Task routes
    task_routes={
        "workers.tasks.stt.*": {"queue": "stt"},
        "workers.tasks.llm.*": {"queue": "llm"},
        "workers.tasks.upload.*": {"queue": "upload"},
    },

    # Define queues
    task_queues=(
        Queue("celery", Exchange("celery"), routing_key="celery"),
        Queue("stt", Exchange("stt"), routing_key="stt"),
        Queue("llm", Exchange("llm"), routing_key="llm"),
        Queue("upload", Exchange("upload"), routing_key="upload"),
    ),

    # Default queue
    task_default_queue="celery",
    task_default_exchange="celery",
    task_default_routing_key="celery",
)

# Auto-discover tasks
celery_app.autodiscover_tasks([
    "workers.tasks",
])


def get_celery_app() -> Celery:
    """Get the Celery application instance."""
    return celery_app
