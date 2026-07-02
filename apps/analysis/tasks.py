from __future__ import annotations

from celery import shared_task

from apps.analysis.models import GameAnalysisJob
from apps.analysis.services import run_game_review


@shared_task(bind=True, autoretry_for=(ConnectionError,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def run_game_analysis_job(self, job_id: str) -> dict:
    job = GameAnalysisJob.objects.select_related("game", "engine_profile").get(pk=job_id)
    return run_game_review(job=job)
