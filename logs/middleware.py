import asyncio

from django.http import HttpResponse
from base.caches import cache
from django.core.handlers.wsgi import WSGIRequest
import logging
from rest_framework import exceptions
from django.conf import settings

from base.wrappers import MockRequest


def get_origin(request: WSGIRequest):
    origin = request.META.get("REMOTE_ADDR", "")
    if not origin:
        origin = request.META.get("HTTP_X_FORWARDED_FOR", "")
    return origin




def handle_request(request: MockRequest):
    user_id = None
    if ip_address := get_origin(request):  # type:ignore
        ip_address = ip_address.split(",")[0]
    else:
        ip_address = None
    if token := getattr(request, "auth", None):
        user_id = token.user_id
    path_info = request.path_info
    from .tasks import create_log

    if path_info.startswith("/gateway/"):
        return
    create_log.delay(
        user_id=user_id,
        ip_address=ip_address,
        path_info=path_info,
        method=request.method,
    )


def request_logger(get_response):
    logger = logging.getLogger("django")

    logger.setLevel(logging.INFO)
    if asyncio.iscoroutinefunction(get_response):

        async def async_middleware(request):
            response = await get_response(request)
            handle_request(request)
            return response

        function = async_middleware
    else:

        def middleware(request):
            response = get_response(request)
            handle_request(request)
            return response

        function = middleware
    return function
