from typing import Optional
from celery import shared_task
from .models import Log


@shared_task
def create_log(
    path_info: Optional[str] = None,
    user_id: Optional[int] = None,
    ip_address: Optional[str] = None,
    method: Optional[str] = None,
    status_code: Optional[int] =200,
):
    Log.objects.create(
        user_id=user_id, ip_address=ip_address, path_info=path_info, method=method,status_code=status_code
    )
