import os
from celery import Celery

# Use the internal Docker DNS to find Redis
redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "orqestra_tasks",
    broker=redis_url,
    backend=redis_url,
    # ADDED: Include the explainability worker so Celery knows about it
    include=["src.workers.tasks", "src.workers.explainability"] 
)

# Route specific tasks to dedicated queues so heavy LLM tasks don't block fast Bouncer tasks
celery_app.conf.task_routes = {
    'src.workers.tasks.extract_and_embed': {'queue': 'claim_extraction'},
    'src.workers.tasks.detect_contradiction': {'queue': 'contradiction_detection'},
    # UPDATED: Correct task name for the explainer
    'src.workers.explainability.generate_explanation_task': {'queue': 'explainability'}, 
}

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)